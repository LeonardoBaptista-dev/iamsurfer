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
    def validate_image(file: FileStorage) -> Tuple[bool, str, Optional[Image.Image]]:
        """
        Valida se o arquivo é uma imagem válida
        
        Returns:
            Tuple[bool, str, Optional[Image.Image]]: (is_valid, error_message, image_object)
        """
        if not file:
            return False, "Nenhum arquivo enviado", None
        
        if file.content_length and file.content_length > ImageProcessor.MAX_FILE_SIZE:
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
        # Valida a imagem
        is_valid, message = cls.validate_image(file)
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
