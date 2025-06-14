import requests
from PIL import Image
import os

# URL do ícone original (que é um PNG disfarçado)
url = 'https://www.iconarchive.com/download/i76029/flat-icons.com/flat-ios-7-style/Music-Note.ico'

# Nomes dos arquivos
png_filename = 'temp_icon.png'
ico_filename = 'icon.ico'

try:
    # Baixar a imagem
    print("Baixando o ícone original...")
    response = requests.get(url)
    response.raise_for_status() # Lança um erro se o download falhar
    
    with open(png_filename, 'wb') as f:
        f.write(response.content)
    
    # Converter de PNG para ICO
    print(f"Convertendo {png_filename} para {ico_filename}...")
    img = Image.open(png_filename)
    img.save(ico_filename, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    
    print("Conversão concluída com sucesso!")

finally:
    # Limpar o arquivo temporário
    if os.path.exists(png_filename):
        os.remove(png_filename)
        print(f"Arquivo temporário {png_filename} removido.")
