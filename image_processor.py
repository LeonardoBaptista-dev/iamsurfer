"""
Sistema de processamento e otimização de imagens para o IAmSurfer
Similar ao Instagram - padronização, compressão e múltiplos tamanhos
"""

import os
import io
import hashlib
from PIL import Image, ImageOps, ExifTags
from typing import Tuple, Dict, Optional
import cloudinary
import cloudinary.uploader
from werkzeug.datastructures import FileStorage

class ImageProcessor:
    """
    Processador de imagens com múltiplos tamanhos e otimização
    """
    
    # Configurações de tamanhos padrão (similar ao Instagram)
    SIZES = {
        'thumbnail': (150, 150),      # Para avatares e previews pequenos
        'small': (320, 320),          # Para feeds mobile
        'medium': (640, 640),         # Para feeds desktop
        'large': (1080, 1080),        # Para visualização completa
        'original': (2048, 2048)      # Máximo permitido
    }
    
    # Qualidades de compressão por tamanho
    QUALITY = {
        'thumbnail': 85,
        'small': 88,
        'medium': 90,
        'large': 92,
        'original': 95
    }
    
    # Formatos suportados
    SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG', 'WEBP'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_image(file: FileStorage, check_size: bool = True) -> Tuple[bool, str, Optional[Image.Image]]:
        """
        Valida se o arquivo é uma imagem válida

        check_size=False pula o limite de tamanho (ex.: foto de perfil) — o
        compressor reduz a imagem, então o usuário pode enviar qualquer tamanho.

        Returns:
            Tuple[bool, str, Optional[Image.Image]]: (is_valid, error_message, image_object)
        """
        if not file:
            return False, "Nenhum arquivo enviado", None

        if check_size and file.content_length and file.content_length > ImageProcessor.MAX_FILE_SIZE:
            return False, "Arquivo muito grande (máximo 10MB)", None
        
        try:
            # Lê o arquivo para verificar se é uma imagem válida
            file.seek(0)
            img = Image.open(file)
            img.verify()
            file.seek(0)  # Reset para uso posterior
            img = Image.open(file)  # Reabre para uso
            
            if img.format not in ImageProcessor.SUPPORTED_FORMATS:
                return False, f"Formato não suportado. Use: {', '.join(ImageProcessor.SUPPORTED_FORMATS)}", None
            
            return True, "Imagem válida", img
        except Exception as e:
            return False, f"Arquivo não é uma imagem válida: {str(e)}", None
    
    @staticmethod
    def fix_image_orientation(img: Image.Image) -> Image.Image:
        """
        Corrige a orientação da imagem baseada nos dados EXIF
        """
        try:
            # Pega os dados EXIF
            exif = img._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    if decoded == 'Orientation':
                        if value == 3:
                            img = img.rotate(180, expand=True)
                        elif value == 6:
                            img = img.rotate(270, expand=True)
                        elif value == 8:
                            img = img.rotate(90, expand=True)
                        break
        except (AttributeError, KeyError, TypeError):
            # Se não conseguir ler EXIF, mantém a imagem como está
            pass
        
        return img
    
    @staticmethod
    def create_square_crop(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """
        Cria um crop quadrado da imagem (similar ao Instagram)
        """
        # Converte para RGB se necessário
        if img.mode in ('RGBA', 'LA', 'P'):
            # Cria fundo branco para transparências
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Usa ImageOps.fit para criar crop centralizado e redimensionar
        img_cropped = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        return img_cropped
    
    @staticmethod
    def create_optimized_image(img: Image.Image, size_name: str) -> bytes:
        """
        Cria uma versão otimizada da imagem
        """
        size = ImageProcessor.SIZES[size_name]
        quality = ImageProcessor.QUALITY[size_name]
        
        # Cria o crop quadrado
        processed_img = ImageProcessor.create_square_crop(img, size)
        
        # Salva em bytes
        output = io.BytesIO()
        
        # Converte para RGB se não for
        if processed_img.mode != 'RGB':
            processed_img = processed_img.convert('RGB')
        
        # Salva como JPEG otimizado
        processed_img.save(
            output,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=True  # JPEG progressivo para carregamento mais rápido
        )
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def generate_image_hash(image_data: bytes) -> str:
        """
        Gera um hash único para a imagem (para evitar duplicatas)
        """
        return hashlib.md5(image_data).hexdigest()
    
    @staticmethod
    def upload_to_cloudinary(image_data: bytes, public_id: str, size_name: str) -> Optional[str]:
        """
        Faz upload da imagem processada para o Cloudinary
        """
        try:
            # Upload para Cloudinary
            result = cloudinary.uploader.upload(
                image_data,
                public_id=f"{public_id}_{size_name}",
                folder="iamsurfer/posts",
                format="jpg",
                quality="auto:good",
                fetch_format="auto"
            )
            return result.get('secure_url')
        except Exception as e:
            print(f"Erro no upload para Cloudinary: {e}")
            return None
    
    @classmethod
    def process_and_upload_image(cls, file: FileStorage, post_id: int) -> Dict[str, str]:
        """
        Processa uma imagem e faz upload de todas as versões
        
        Returns:
            Dict com URLs de todos os tamanhos ou erro
        """
        # Valida a imagem (validate_image retorna 3 valores; sem limite de
        # tamanho — o processamento abaixo já reduz/otimiza)
        is_valid, message, _img = cls.validate_image(file, check_size=False)
        if not is_valid:
            return {'error': message}
        
        try:
            # Abre a imagem original
            file.seek(0)
            original_img = Image.open(file)
            
            # Corrige orientação
            original_img = cls.fix_image_orientation(original_img)
            
            # Gera hash único
            file.seek(0)
            image_hash = cls.generate_image_hash(file.read())
            
            # ID único para esta imagem
            unique_id = f"post_{post_id}_{image_hash[:8]}"
            
            # Processa e faz upload de cada tamanho
            urls = {}
            
            for size_name in cls.SIZES.keys():
                try:
                    # Cria versão otimizada
                    optimized_data = cls.create_optimized_image(original_img, size_name)
                    
                    # Faz upload para Cloudinary
                    url = cls.upload_to_cloudinary(optimized_data, unique_id, size_name)
                    
                    if url:
                        urls[size_name] = url
                    else:
                        print(f"Falha no upload do tamanho {size_name}")
                        
                except Exception as e:
                    print(f"Erro processando tamanho {size_name}: {e}")
                    continue
            
            if not urls:
                return {'error': 'Falha no processamento da imagem'}
            
            # Retorna todas as URLs
            return {
                'success': True,
                'urls': urls,
                'hash': image_hash
            }
            
        except Exception as e:
            return {'error': f'Erro no processamento: {str(e)}'}

    @classmethod
    def process_and_upload_video(cls, file: FileStorage, post_id: int, is_reel: bool = False) -> Dict[str, str]:
        """
        Comprime o vídeo localmente (FFmpeg, ~8MB no máximo) ANTES de subir e só
        então envia o arquivo já reduzido ao Cloudinary. Isso evita que o
        Cloudinary guarde o arquivo original gigante do celular e estoure a cota.

        Se o FFmpeg não estiver disponível, faz fallback subindo o original com
        um limite de resolução do próprio Cloudinary.
        """
        import os
        import uuid
        import tempfile
        from video_utils import compress_video, ffmpeg_available

        unique_id = f"video_post_{post_id}_{uuid.uuid4().hex[:8]}"
        tmp_dir = tempfile.mkdtemp(prefix="iamsurfer_vid_")
        raw_ext = (file.filename.rsplit('.', 1)[-1].lower() if '.' in (file.filename or '') else 'mp4')
        raw_path = os.path.join(tmp_dir, f"raw_{unique_id}.{raw_ext}")
        out_path = os.path.join(tmp_dir, f"out_{unique_id}.mp4")

        def _cleanup():
            for p in (raw_path, out_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

        try:
            file.seek(0)
            file.save(raw_path)

            upload_path = raw_path
            extra = {}

            if ffmpeg_available():
                ok, msg = compress_video(raw_path, out_path, target_mb=8, is_reel=is_reel)
                print(f"[video] {msg}")
                if ok and os.path.exists(out_path):
                    upload_path = out_path
                else:
                    # Compressão falhou: deixa o Cloudinary ao menos limitar a resolução
                    extra = {"eager": [{"width": 1280, "crop": "limit"}], "eager_async": True}
            else:
                print("[video] FFmpeg indisponível — subindo original com limite do Cloudinary")
                extra = {"eager": [{"width": 1280, "crop": "limit"}], "eager_async": True}

            result = cloudinary.uploader.upload(
                upload_path,
                resource_type="video",
                public_id=unique_id,
                folder="iamsurfer/posts/videos",
                **extra,
            )

            url = result.get('secure_url')
            if url:
                return {'success': True, 'url': url}
            return {'error': 'Falha na resposta ao enviar vídeo para Cloudinary'}

        except Exception as e:
            return {'error': f'Erro no processamento de vídeo: {str(e)}'}
        finally:
            _cleanup()

    # ── Perfil (avatares) ───────────────────────────────────────────────
    # Espelha os tamanhos do processador local, mas sobe pro Cloudinary para
    # PERSISTIR (o disco do container é efêmero). Mesma assinatura de retorno
    # do LocalImageProcessor.process_and_save_profile: (ok, msg, urls).

    PROFILE_SIZES = {
        'thumbnail': (64, 64),
        'small': (150, 150),
        'medium': (300, 300),
        'large': (600, 600),
    }
    PROFILE_QUALITY = {
        'thumbnail': 90, 'small': 92, 'medium': 94, 'large': 96,
    }

    @staticmethod
    def _optimized_square_bytes(img: Image.Image, size: Tuple[int, int], quality: int) -> bytes:
        cropped = ImageProcessor.create_square_crop(img, size)
        if cropped.mode != 'RGB':
            cropped = cropped.convert('RGB')
        out = io.BytesIO()
        cropped.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
        out.seek(0)
        return out.getvalue()

    @staticmethod
    def upload_profile_to_cloudinary(image_data: bytes, public_id: str, size_name: str) -> Optional[str]:
        try:
            result = cloudinary.uploader.upload(
                image_data,
                public_id=f"{public_id}_{size_name}",
                folder="iamsurfer/profiles",
                format="jpg",
                quality="auto:good",
                fetch_format="auto",
            )
            return result.get('secure_url')
        except Exception as e:
            print(f"Erro no upload de perfil para Cloudinary: {e}")
            return None

    @staticmethod
    def process_and_save_profile(file: FileStorage) -> Tuple[bool, str, Optional[Dict[str, str]]]:
        """Processa o avatar em vários tamanhos e sobe pro Cloudinary."""
        # Sem limite de tamanho: o compressor reduz a imagem
        is_valid, error_msg, img = ImageProcessor.validate_image(file, check_size=False)
        if not is_valid:
            return False, error_msg, None
        try:
            img = ImageProcessor.fix_image_orientation(img)
            file.seek(0)
            file_hash = hashlib.md5(file.read()).hexdigest()
            file.seek(0)
            unique_id = f"profile_{file_hash[:10]}"

            urls = {}
            for size_name, size in ImageProcessor.PROFILE_SIZES.items():
                data = ImageProcessor._optimized_square_bytes(
                    img, size, ImageProcessor.PROFILE_QUALITY[size_name]
                )
                url = ImageProcessor.upload_profile_to_cloudinary(data, unique_id, size_name)
                if url:
                    urls[size_name] = url

            if not urls:
                return False, "Falha no upload da imagem de perfil", None
            return True, "Imagem de perfil processada com sucesso", urls
        except Exception as e:
            return False, f"Erro ao processar imagem de perfil: {str(e)}", None


class ResponsiveImageHelper:
    """
    Helper para gerar tags de imagem responsivas nos templates
    """
    
    @staticmethod
    def get_responsive_img_tag(urls: Dict[str, str], alt: str = "", css_class: str = "") -> str:
        """
        Gera uma tag img responsiva com srcset
        """
        if not urls:
            return ""
        
        # URL principal (medium como padrão)
        main_url = urls.get('medium', urls.get('small', list(urls.values())[0]))
        
        # Cria srcset para diferentes densidades
        srcset_parts = []
        
        if 'small' in urls:
            srcset_parts.append(f"{urls['small']} 320w")
        if 'medium' in urls:
            srcset_parts.append(f"{urls['medium']} 640w")
        if 'large' in urls:
            srcset_parts.append(f"{urls['large']} 1080w")
        
        srcset = ", ".join(srcset_parts)
        
        # Tamanhos responsivos
        sizes = "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        
        return f'''<img src="{main_url}" 
                       srcset="{srcset}" 
                       sizes="{sizes}"
                       alt="{alt}" 
                       class="{css_class}"
                       loading="lazy">'''
    
    @staticmethod
    def get_thumbnail_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL do thumbnail
        """
        return urls.get('thumbnail', urls.get('small', ''))
    
    @staticmethod
    def get_feed_url(urls: Dict[str, str], is_mobile: bool = False) -> str:
        """
        Retorna URL apropriada para feed
        """
        if is_mobile:
            return urls.get('small', urls.get('medium', ''))
        return urls.get('medium', urls.get('large', ''))

    # ── Perfil (avatares) ───────────────────────────────────────────────
    # Em produção os avatares ficam no Cloudinary (URLs http absolutas). Dados
    # legados podem ter caminhos LOCAIS (de uploads antigos para o disco efêmero,
    # já perdidos): nesse caso caímos no avatar padrão em vez de quebrar/404.

    DEFAULT_PROFILE = "/static/uploads/default_profile.jpg"

    @staticmethod
    def _profile_or_default(value: str) -> str:
        if value and value.startswith('http'):
            return value
        return ResponsiveImageHelper.DEFAULT_PROFILE

    @staticmethod
    def get_profile_thumbnail_url(urls: Dict[str, str]) -> str:
        if not urls:
            return ResponsiveImageHelper.DEFAULT_PROFILE
        return ResponsiveImageHelper._profile_or_default(urls.get('thumbnail', urls.get('small', '')))

    @staticmethod
    def get_profile_avatar_url(urls: Dict[str, str]) -> str:
        if not urls:
            return ResponsiveImageHelper.DEFAULT_PROFILE
        return ResponsiveImageHelper._profile_or_default(urls.get('small', urls.get('thumbnail', '')))

    @staticmethod
    def get_profile_medium_url(urls: Dict[str, str]) -> str:
        if not urls:
            return ResponsiveImageHelper.DEFAULT_PROFILE
        return ResponsiveImageHelper._profile_or_default(urls.get('medium', urls.get('small', '')))

    @staticmethod
    def get_profile_large_url(urls: Dict[str, str]) -> str:
        if not urls:
            return ResponsiveImageHelper.DEFAULT_PROFILE
        return ResponsiveImageHelper._profile_or_default(urls.get('large', urls.get('medium', '')))

    @staticmethod
    def get_profile_avatar_tag(urls: Dict[str, str], alt: str = "", css_class: str = "rounded-circle", size: str = "small") -> str:
        if not urls:
            return f'<img src="{ResponsiveImageHelper.DEFAULT_PROFILE}" alt="{alt}" class="{css_class}" loading="lazy">'
        main = ResponsiveImageHelper._profile_or_default(urls.get(size, urls.get('small', urls.get('thumbnail', ''))))
        # srcset só com URLs válidas (http) do Cloudinary
        parts = []
        for key, w in (('thumbnail', 64), ('small', 150), ('medium', 300)):
            v = urls.get(key, '')
            if v and v.startswith('http'):
                parts.append(f"{v} {w}w")
        srcset = ", ".join(parts)
        srcset_attr = f' srcset="{srcset}" sizes="(max-width: 768px) 64px, 150px"' if srcset else ''
        return f'<img src="{main}"{srcset_attr} alt="{alt}" class="{css_class}" loading="lazy">'
