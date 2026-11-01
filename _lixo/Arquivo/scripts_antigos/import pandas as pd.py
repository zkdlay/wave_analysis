import pandas as pd
import matplotlib.pyplot as plt

# carregar dados
df = pd.read_excel(r"C:\Users\Windows\OneDrive\Documentos\Iniciação Cientifica - INPE\analises_2025\table_onehour.xlsx")

# converter data
df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])

# gráfico temperatura
plt.figure()
plt.plot(df['TIMESTAMP'], df['Temperatura_Avg'])
plt.xlabel('Tempo')
plt.ylabel('Temperatura (°C)')
plt.title('Temperatura do ar')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('temperatura.png')
plt.show()

# gráfico umidade
plt.figure()
plt.plot(df['TIMESTAMP'], df['Umidade_Avg'])
plt.xlabel('Tempo')
plt.ylabel('Umidade relativa (%)')
plt.title('Umidade relativa do ar')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('umidade.png')
plt.show()