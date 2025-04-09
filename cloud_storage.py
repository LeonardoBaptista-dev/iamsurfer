import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app

# Inicializa o Cloudinary
def init_cloudinary():
    """Inicializa a configuração do Cloudinary a partir das variáveis de ambiente"""
    try:
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
            secure=True
        )
        print("✅ Cloudinary configurado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao configurar Cloudinary: {str(e)}")
        return False

def upload_file(file, folder='uploads'):
    """Faz upload de um arquivo para o Cloudinary
    
    Args:
        file: Objeto de arquivo enviado pelo usuário
        folder: Pasta no Cloudinary para organizar os arquivos
        
    Returns:
        URL pública do arquivo enviado
    """
    if not file:
        return None
    
    try:
        # Faz o upload do arquivo para o Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="auto",  # Detecta automaticamente o tipo de arquivo
            unique_filename=True,  # Garante um nome único
            overwrite=False        # Não sobrescreve arquivos existentes
        )
        
        # Retorna a URL pública do arquivo
        return result['secure_url']
    except Exception as e:
        print(f"Erro ao fazer upload para Cloudinary: {str(e)}")
        return None

def delete_file(public_id_or_url):
    """Exclui um arquivo do Cloudinary
    
    Args:
        public_id_or_url: ID público ou URL do arquivo no Cloudinary
        
    Returns:
        Booleano indicando sucesso ou falha
    """
    if not public_id_or_url:
        return False
    
    try:
        # Se for uma URL, tenta extrair o public_id
        if public_id_or_url.startswith('http'):
            try:
                # Extrai o public_id da URL do Cloudinary
                # Exemplo: https://res.cloudinary.com/dekstvey2/image/upload/v1234567890/folder/filename.jpg
                parts = public_id_or_url.split('/')
                
                # Encontra o índice da versão (começa com 'v' seguido de números)
                version_idx = None
                for i, part in enumerate(parts):
                    if part.startswith('v') and part[1:].isdigit():
                        version_idx = i
                        break
                
                if version_idx is not None:
                    # O public_id é tudo após o número da versão
                    public_id = '/'.join(parts[version_idx+1:])
                    
                    # Detecta o tipo de recurso (image, video, raw, etc.)
                    resource_type = "image"  # Padrão
                    if "image" in parts:
                        resource_type = "image"
                    elif "video" in parts:
                        resource_type = "video"
                    elif "raw" in parts:
                        resource_type = "raw"
                    
                    # Exclui o arquivo
                    result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
                    return result.get('result') == 'ok'
                else:
                    print(f"Aviso: Não foi possível extrair public_id da URL: {public_id_or_url}")
                    return False
            except Exception as e:
                print(f"Erro ao processar URL do Cloudinary: {str(e)}")
                return False
        else:
            # Se não for URL, assume que é um public_id direto
            result = cloudinary.uploader.destroy(public_id_or_url)
            return result.get('result') == 'ok'
    except Exception as e:
        print(f"Erro ao excluir arquivo do Cloudinary: {str(e)}")
        return False 