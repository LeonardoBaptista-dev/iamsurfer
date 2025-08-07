"""
Sistema de processamento e otimização de imagens para desenvolvimento local
Similar ao Instagram - padronização, compressão e múltiplos tamanhos
Salva arquivos localmente em vez de usar Cloudinary
"""

import os
import io
import hashlib
import uuid
from PIL import Image, ImageOps, ExifTags
from typing import Tuple, Dict, Optional
from werkzeug.datastructures import FileStorage
from flask import current_app, url_for

class LocalImageProcessor:
    """
    Processador de imagens local com múltiplos tamanhos e otimização
    """
    
    # Configurações de tamanhos padrão (similar ao Instagram)
    SIZES = {
        'thumbnail': (150, 150),      # Para avatares e previews pequenos
        'small': (320, 320),          # Para feeds mobile
        'medium': (640, 640),         # Para feeds desktop
        'large': (1080, 1080),        # Para visualização completa
        'original': (2048, 2048)      # Máximo permitido
    }
    
    # Tamanhos específicos para perfil (otimizados para avatares)
    PROFILE_SIZES = {
        'thumbnail': (64, 64),        # Avatar muito pequeno (lista de comentários)
        'small': (150, 150),          # Avatar padrão (navbar, cards)
        'medium': (300, 300),         # Perfil médio (página de perfil)
        'large': (600, 600),          # Visualização completa do perfil
        'original': (800, 800)        # Máximo para perfil
    }
    
    # Qualidades de compressão por tamanho
    QUALITY = {
        'thumbnail': 85,
        'small': 88,
        'medium': 90,
        'large': 92,
        'original': 95
    }
    
    # Qualidades específicas para perfil (um pouco mais altas para avatares)
    PROFILE_QUALITY = {
        'thumbnail': 90,
        'small': 92,
        'medium': 94,
        'large': 96,
        'original': 98
    }
    
    # Formatos suportados
    SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG', 'WEBP'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_image(file: FileStorage) -> Tuple[bool, str, Optional[Image.Image]]:
        """
        Valida se o arquivo é uma imagem válida
        
        Returns:
            Tuple[bool, str, Optional[Image.Image]]: (is_valid, error_message, image_object)
        """
        if not file:
            return False, "Nenhum arquivo fornecido", None
            
        # Verifica o tamanho do arquivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > LocalImageProcessor.MAX_FILE_SIZE:
            return False, f"Arquivo muito grande. Máximo: {LocalImageProcessor.MAX_FILE_SIZE // (1024*1024)}MB", None
        
        if file_size == 0:
            return False, "Arquivo vazio", None
        
        try:
            # Tenta abrir como imagem
            img = Image.open(file)
            img.verify()  # Verifica se é uma imagem válida
            
            # Reabre a imagem pois verify() a corrompe
            file.seek(0)
            img = Image.open(file)
            
            # Verifica formato
            if img.format not in LocalImageProcessor.SUPPORTED_FORMATS:
                return False, f"Formato não suportado. Use: {', '.join(LocalImageProcessor.SUPPORTED_FORMATS)}", None
            
            # Verifica dimensões mínimas
            if img.width < 100 or img.height < 100:
                return False, "Imagem muito pequena. Mínimo: 100x100 pixels", None
                
            return True, "", img
            
        except Exception as e:
            return False, f"Arquivo não é uma imagem válida: {str(e)}", None
    
    @staticmethod
    def create_square_crop(img: Image.Image) -> Image.Image:
        """
        Cria um crop quadrado centralizado da imagem
        """
        # Corrige orientação baseada nos dados EXIF
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # Ignora se não conseguir corrigir EXIF
        
        # Converte para RGB se necessário
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calcula o crop quadrado
        width, height = img.size
        size = min(width, height)
        
        # Centraliza o crop
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        
        return img.crop((left, top, right, bottom))
    
    @staticmethod
    def resize_and_optimize(img: Image.Image, size: Tuple[int, int], quality: int) -> io.BytesIO:
        """
        Redimensiona e otimiza a imagem
        """
        # Redimensiona mantendo proporção
        img_resized = img.resize(size, Image.Resampling.LANCZOS)
        
        # Salva em buffer com otimização
        buffer = io.BytesIO()
        img_resized.save(
            buffer,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=True
        )
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_filename(original_filename: str, size: str, file_hash: str) -> str:
        """
        Gera nome único para o arquivo
        """
        # Remove extensão original
        name_without_ext = os.path.splitext(original_filename)[0]
        # Limpa o nome do arquivo
        clean_name = "".join(c for c in name_without_ext if c.isalnum() or c in (' ', '-', '_'))[:20]
        
        # Gera nome único
        unique_id = str(uuid.uuid4())[:8]
        return f"{clean_name}_{file_hash[:8]}_{size}_{unique_id}.jpg"
    
    @staticmethod
    def ensure_upload_dir() -> str:
        """
        Garante que a pasta de uploads existe
        """
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'posts')
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir
    
    @staticmethod
    def save_local_file(buffer: io.BytesIO, filename: str) -> str:
        """
        Salva arquivo localmente na estrutura organizada por tamanho
        """
        # Extrai o tamanho do nome do arquivo (último elemento antes da extensão)
        name_parts = filename.replace('.jpg', '').split('_')
        size = name_parts[-1]  # thumbnail, small, medium, large, original
        
        # Cria estrutura de pastas organizadas
        relative_dir = f"uploads/posts/{size}"
        full_dir = os.path.join(current_app.root_path, 'static', relative_dir)
        os.makedirs(full_dir, exist_ok=True)
        
        # Salva o arquivo
        file_path = os.path.join(full_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Retorna caminho relativo para URLs
        return f"{relative_dir}/{filename}"
    
    @staticmethod
    def process_and_save(file: FileStorage) -> Tuple[bool, str, Optional[Dict[str, str]]]:
        """
        Processa imagem em múltiplos tamanhos e salva localmente
        
        Returns:
            Tuple[bool, str, Optional[Dict[str, str]]]: (success, message, urls_dict)
        """
        # Validação
        is_valid, error_msg, img = LocalImageProcessor.validate_image(file)
        if not is_valid:
            return False, error_msg, None
        
        try:
            # Gera hash do arquivo original
            file.seek(0)
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            file.seek(0)
            
            # Cria crop quadrado
            img_square = LocalImageProcessor.create_square_crop(img)
            
            # Processa cada tamanho
            urls = {}
            
            for size_name, (width, height) in LocalImageProcessor.SIZES.items():
                # Redimensiona e otimiza
                buffer = LocalImageProcessor.resize_and_optimize(
                    img_square, 
                    (width, height), 
                    LocalImageProcessor.QUALITY[size_name]
                )
                
                # Gera nome do arquivo
                filename = LocalImageProcessor.generate_filename(
                    file.filename, 
                    size_name, 
                    file_hash
                )
                
                # Salva localmente
                relative_path = LocalImageProcessor.save_local_file(buffer, filename)
                urls[size_name] = relative_path
            
            return True, "Imagem processada com sucesso", urls
            
        except Exception as e:
            return False, f"Erro ao processar imagem: {str(e)}", None
    
    @staticmethod
    def delete_image_files(urls: Dict[str, str]):
        """
        Remove arquivos de imagem do sistema local
        """
        try:
            for url in urls.values():
                if url and not url.startswith('http'):
                    file_path = os.path.join(current_app.root_path, 'static', url)
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Erro ao deletar arquivos: {e}")


class ResponsiveImageHelper:
    """
    Helper para gerar HTML e URLs de imagens responsivas
    """
    
    @staticmethod
    def get_responsive_img_tag(urls: Dict[str, str], alt: str = "", css_class: str = "") -> str:
        """
        Gera tag img com srcset para imagens responsivas
        """
        if not urls:
            return f'<img src="/static/uploads/default_post.jpg" alt="{alt}" class="{css_class}" loading="lazy">'
        
        # Define a imagem principal (medium como padrão)
        main_src = urls.get('medium', urls.get('small', ''))
        
        # Cria srcset para diferentes densidades
        srcset_parts = []
        if 'small' in urls:
            srcset_parts.append(f"/static/{urls['small']} 320w")
        if 'medium' in urls:
            srcset_parts.append(f"/static/{urls['medium']} 640w")
        if 'large' in urls:
            srcset_parts.append(f"/static/{urls['large']} 1080w")
        
        srcset = ", ".join(srcset_parts)
        
        return f'''<img 
            src="/static/{main_src}" 
            srcset="{srcset}" 
            sizes="(max-width: 480px) 320px, (max-width: 768px) 640px, 1080px"
            alt="{alt}" 
            class="{css_class}" 
            loading="lazy"
        >'''
    
    @staticmethod
    def get_thumbnail_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL do thumbnail
        """
        if not urls:
            return "/static/uploads/default_post.jpg"
        return f"/static/{urls.get('thumbnail', urls.get('small', ''))}"
    
    @staticmethod
    def get_feed_url(urls: Dict[str, str], is_mobile: bool = False) -> str:
        """
        Retorna URL apropriada para feed
        """
        if not urls:
            return "/static/uploads/default_post.jpg"
        
        if is_mobile:
            return f"/static/{urls.get('small', urls.get('medium', ''))}"
        else:
            return f"/static/{urls.get('medium', urls.get('small', ''))}"
    
    @staticmethod
    def get_large_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL da imagem grande
        """
        if not urls:
            return "/static/uploads/default_post.jpg"
        return f"/static/{urls.get('large', urls.get('original', urls.get('medium', '')))}"
    
    @staticmethod
    def process_and_save_profile(file: FileStorage) -> Tuple[bool, str, Optional[Dict[str, str]]]:
        """
        Processa imagem de perfil em múltiplos tamanhos otimizados para avatares
        
        Returns:
            Tuple[bool, str, Optional[Dict[str, str]]]: (success, message, urls_dict)
        """
        # Validação
        is_valid, error_msg, img = LocalImageProcessor.validate_image(file)
        if not is_valid:
            return False, error_msg, None
        
        try:
            # Gera hash do arquivo original
            file.seek(0)
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            file.seek(0)
            
            # Cria crop quadrado (essencial para avatares)
            img_square = LocalImageProcessor.create_square_crop(img)
            
            # Processa cada tamanho específico para perfil
            urls = {}
            
            for size_name, (width, height) in LocalImageProcessor.PROFILE_SIZES.items():
                # Redimensiona e otimiza com qualidade específica para perfil
                buffer = LocalImageProcessor.resize_and_optimize(
                    img_square, 
                    (width, height), 
                    LocalImageProcessor.PROFILE_QUALITY[size_name]
                )
                
                # Gera nome do arquivo com prefixo profile
                filename = f"profile_{LocalImageProcessor.generate_filename(file.filename, size_name, file_hash)}"
                
                # Salva na pasta profiles com subpastas por tamanho
                relative_path = LocalImageProcessor.save_profile_file(buffer, filename, size_name)
                urls[size_name] = relative_path
            
            return True, "Imagem de perfil processada com sucesso", urls
            
        except Exception as e:
            return False, f"Erro ao processar imagem de perfil: {str(e)}", None

    @staticmethod
    def save_profile_file(buffer: io.BytesIO, filename: str, size: str) -> str:
        """
        Salva arquivo de perfil na estrutura organizada
        """
        # Cria estrutura de pastas para perfis
        relative_dir = f"uploads/profiles/{size}"
        full_dir = os.path.join(current_app.root_path, 'static', relative_dir)
        os.makedirs(full_dir, exist_ok=True)
        
        # Salva o arquivo
        file_path = os.path.join(full_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Retorna caminho relativo para URLs
        return f"{relative_dir}/{filename}"
    
    @staticmethod
    def get_profile_avatar_tag(urls: Dict[str, str], alt: str = "", css_class: str = "rounded-circle", size: str = "small") -> str:
        """
        Gera tag img otimizada para avatares de perfil
        """
        if not urls:
            return f'<img src="/static/uploads/default_profile.jpg" alt="{alt}" class="{css_class}" loading="lazy">'
        
        # URL principal baseada no tamanho solicitado
        main_src = urls.get(size, urls.get('small', urls.get('thumbnail', 'uploads/default_profile.jpg')))
        
        # Monta srcset específico para avatares
        srcset_parts = []
        if 'thumbnail' in urls:
            srcset_parts.append(f"/static/{urls['thumbnail']} 64w")
        if 'small' in urls:
            srcset_parts.append(f"/static/{urls['small']} 150w")
        if 'medium' in urls:
            srcset_parts.append(f"/static/{urls['medium']} 300w")
        
        srcset = ", ".join(srcset_parts)
        
        return f'''<img 
            src="/static/{main_src}" 
            srcset="{srcset}" 
            sizes="(max-width: 768px) 64px, 150px"
            alt="{alt}" 
            class="{css_class}" 
            loading="lazy"
        >'''
    
    @staticmethod
    def get_profile_thumbnail_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL do thumbnail de perfil (64x64)
        """
        if not urls:
            return "/static/uploads/default_profile.jpg"
        return f"/static/{urls.get('thumbnail', urls.get('small', 'uploads/default_profile.jpg'))}"
    
    @staticmethod
    def get_profile_avatar_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL do avatar padrão de perfil (150x150)
        """
        if not urls:
            return "/static/uploads/default_profile.jpg"
        return f"/static/{urls.get('small', urls.get('thumbnail', 'uploads/default_profile.jpg'))}"
    
    @staticmethod
    def get_profile_medium_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL da imagem média de perfil (300x300)
        """
        if not urls:
            return "/static/uploads/default_profile.jpg"
        return f"/static/{urls.get('medium', urls.get('small', 'uploads/default_profile.jpg'))}"
    
    @staticmethod
    def get_profile_large_url(urls: Dict[str, str]) -> str:
        """
        Retorna URL da imagem grande de perfil (600x600)
        """
        if not urls:
            return "/static/uploads/default_profile.jpg"
        return f"/static/{urls.get('large', urls.get('medium', 'uploads/default_profile.jpg'))}"
