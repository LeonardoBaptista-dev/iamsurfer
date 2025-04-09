import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração
cloudinary.config( 
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

print("Configuração do Cloudinary:")
print(f"Cloud name: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")
print(f"API key: {os.environ.get('CLOUDINARY_API_KEY')}")
print(f"API secret: {'*' * len(os.environ.get('CLOUDINARY_API_SECRET', ''))}")

# Cria um arquivo de teste simples
test_file_path = 'test_image.txt'
with open(test_file_path, 'w') as f:
    f.write("This is a test file for Cloudinary upload")

print("Arquivo de teste criado.")

try:
    # Tenta fazer upload do arquivo
    print("Fazendo upload para o Cloudinary...")
    upload_result = cloudinary.uploader.upload(test_file_path, 
                                      folder="test",
                                      resource_type="raw")
    
    print("✅ Upload realizado com sucesso!")
    print(f"URL do arquivo: {upload_result['secure_url']}")
    
    # Tenta excluir o arquivo
    print("Tentando excluir o arquivo...")
    public_id = upload_result['public_id']
    delete_result = cloudinary.uploader.destroy(public_id, resource_type="raw")
    
    if delete_result.get('result') == 'ok':
        print("✅ Arquivo excluído com sucesso!")
    else:
        print(f"❌ Falha ao excluir arquivo: {delete_result}")
except Exception as e:
    print(f"❌ Erro: {str(e)}")
finally:
    # Remove o arquivo de teste local
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("Arquivo de teste local removido.") 