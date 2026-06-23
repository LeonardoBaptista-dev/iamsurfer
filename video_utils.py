"""
Compressão de vídeo compartilhada (dev local e produção/Cloudinary).

Objetivo: reduzir vídeos de celular (alta resolução, dezenas de MB) para um
arquivo pequeno (~8MB no máximo) ANTES de qualquer upload, para não estourar a
cota do Cloudinary. Usa FFmpeg em dois passos (two-pass) para acertar o tamanho
final a partir de um bitrate calculado pela duração do vídeo.

Se o FFmpeg/FFprobe não estiver disponível, as funções retornam (False, msg)
para que o chamador possa decidir o fallback.
"""

import os
import subprocess
import uuid

# Caixa máxima (em px) na qual o vídeo é encaixado mantendo o aspect ratio.
# 1280 deixa reels verticais em ~720x1280 e vídeos horizontais em ~1280x720 —
# bom equilíbrio entre qualidade e economia de cota.
MAX_DIMENSION = 1280

# Margem de segurança para o tamanho-alvo (o two-pass costuma ficar um pouco
# acima do bitrate médio pedido; 0.92 garante folga sob o limite).
SIZE_SAFETY = 0.92

AUDIO_KBPS = 96
MIN_VIDEO_KBPS = 300
MAX_VIDEO_KBPS = 4000


def ffmpeg_available() -> bool:
    """Retorna True se ffmpeg e ffprobe estão no PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(['ffprobe', '-version'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def probe_duration(path: str):
    """Duração do vídeo em segundos (float) ou None se não conseguir ler."""
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
        )
        return float(out.stdout.decode().strip())
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        return None


def _scale_filter() -> str:
    """Encaixa o vídeo numa caixa MAX_DIMENSION mantendo aspect ratio e
    garantindo dimensões pares (exigência do H.264)."""
    return (
        f"scale=w={MAX_DIMENSION}:h={MAX_DIMENSION}:force_original_aspect_ratio=decrease,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2"
    )


def compress_video(input_path: str, output_path: str, target_mb: int = 8,
                   is_reel: bool = False) -> tuple:
    """
    Comprime input_path -> output_path tentando ficar <= target_mb.

    Returns: (success: bool, message: str)
    """
    if not ffmpeg_available():
        return False, "FFmpeg não disponível"

    duration = probe_duration(input_path)
    scale = _scale_filter()
    # Log de passagem único, na mesma pasta do output (evita colisão entre uploads).
    passlog = os.path.join(os.path.dirname(output_path) or '.',
                           f"ffpass_{uuid.uuid4().hex}")

    try:
        if duration and duration > 0:
            # bitrate total alvo (kbps) = bits do arquivo / duração
            target_total_kbps = (target_mb * 1024 * 1024 * 8 * SIZE_SAFETY) / duration / 1000
            video_kbps = int(target_total_kbps - AUDIO_KBPS)
            video_kbps = max(MIN_VIDEO_KBPS, min(MAX_VIDEO_KBPS, video_kbps))

            common = ['-c:v', 'libx264', '-b:v', f'{video_kbps}k',
                      '-vf', scale, '-preset', 'medium', '-pix_fmt', 'yuv420p']

            # Passo 1 (sem áudio, descarta saída)
            subprocess.run(
                ['ffmpeg', '-y', '-i', input_path, *common,
                 '-pass', '1', '-passlogfile', passlog, '-an', '-f', 'mp4', os.devnull],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
            # Passo 2 (com áudio, gera o arquivo final)
            subprocess.run(
                ['ffmpeg', '-y', '-i', input_path, *common,
                 '-pass', '2', '-passlogfile', passlog,
                 '-c:a', 'aac', '-b:a', f'{AUDIO_KBPS}k',
                 '-movflags', '+faststart', output_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
            msg = f"Vídeo comprimido (~{video_kbps}kbps de vídeo, alvo {target_mb}MB)"
        else:
            # Sem duração confiável: cai para CRF single-pass (sem alvo exato de tamanho)
            subprocess.run(
                ['ffmpeg', '-y', '-i', input_path,
                 '-c:v', 'libx264', '-crf', '30', '-preset', 'medium',
                 '-vf', scale, '-pix_fmt', 'yuv420p',
                 '-c:a', 'aac', '-b:a', f'{AUDIO_KBPS}k',
                 '-movflags', '+faststart', output_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
            )
            msg = "Vídeo comprimido (CRF 30, sem duração detectada)"

        return True, msg

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return False, f"Falha na compressão FFmpeg: {e}"
    finally:
        # Limpa os logs de two-pass
        for suffix in ('', '-0.log', '-0.log.mbtree', '.log', '.log.mbtree'):
            p = passlog + suffix
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
