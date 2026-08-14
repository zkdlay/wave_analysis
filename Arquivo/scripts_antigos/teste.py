#Marca, cor, preço
class Carro:
    def __init__(self, marca, cor, preco):
        self.marca=marca
        self.cor=cor
        self.preco=preco

    def testdrive(self):
        return 'Vou fazer um teste drive'

    def comprar(self):
        return 'estou comprando esse carro'

    def exibe_info(self):
       print(self.marca, self.cor, self.preco)
    
carro1=Carro('Toyota', 'preto', 'R$ 150.000,00')
carro1.exibe_info()
carro1.testdrive()
carro1.comprar()