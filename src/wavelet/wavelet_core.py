import numpy as np 
from scipy.special import gamma
from scipy.stats import chi2

def wavelet(Y, dt, pad=0, dj=-1, s0=-1, J1=-1, mother=-1, freq=None):
    """
    Função para calcular a transformada wavelet contínua.
    """
    n1 = len(Y)

    # Definição de parâmetros padrão, caso não sejam fornecidos
    if s0 == -1:
        s0 = 2 * dt
    if dj == -1:
        dj = 1. / 4.
    if J1 == -1:
        J1 = np.fix((np.log(n1 * dt / s0) / np.log(2)) / dj)
    if mother == -1:
        mother = 'MORLET'

    # Centralizando a série temporal (removendo a média)
    x = Y - np.mean(Y)
    
    # Padding para tornar o tamanho da série um número potência de 2
    if pad == 1:
        base2 = np.fix(np.log(n1) / np.log(2) + 0.4999)
        nzeroes = (2 ** (base2 + 1) - n1).astype(np.int64)
        x = np.concatenate((x, np.zeros(nzeroes)))
    n = len(x)

    # Construção do vetor de números de onda
    kplus = np.arange(1, int(n/2)+1) * (2 * np.pi / (n * dt))
    kminus = -np.arange(1, int((n-1)/2)+1) * (2 * np.pi / (n * dt))
    k = np.concatenate(([0.], kplus, np.flip(kminus)))

    # Cálculo da FFT da série temporal
    f = np.fft.fft(x)
    
    # Determinação do fator de Fourier conforme a wavelet mãe
    if mother.upper() == 'MORLET':
        param = 6.
        fourier_factor = 4 * np.pi / (param + np.sqrt(2 + param ** 2))
    elif mother.upper() == 'PAUL':
        param = 4.
        fourier_factor = 4 * np.pi / (2 * param + 1)
    elif mother.upper() == 'DOG':
        param = 2.
        fourier_factor = 2 * np.pi * np.sqrt(2. / (2 * param + 1))
    else:
        raise ValueError("Wavelet mãe desconhecida")
    
    # Definição das escalas
    if freq is None:
        j = np.arange(0, J1 + 1)
        scale = s0 * 2. ** (j * dj)
        freq = 1. / (fourier_factor * scale)
    else:
        scale = 1. / (fourier_factor * freq)
    
    period = 1. / freq
    wave = np.zeros((len(scale), n), dtype=complex)
    
    # Cálculo da transformada wavelet para cada escala
    for a1 in range(len(scale)):
        daughter, _, coi, _ = wave_bases(mother, k, scale[a1], param)
        wave[a1, :] = np.fft.ifft(f * daughter)
    
    # Construção da região de influência cônica (COI)
    coi = coi * dt * np.concatenate((
        np.insert(np.arange(int((n1 + 1) / 2) - 1), [0], [1E-5]),
        np.insert(np.flip(np.arange(0, int(n1 / 2) - 1)), [-1], [1E-5])
    ))
    
    return wave[:, :n1], period, scale, coi

def wave_bases(mother, k, scale, param):
    """
    Gera as funções base das wavelets Morlet, Paul e DOG.
    """
    n = len(k)
    kplus = (k > 0).astype(float)

    if mother == 'MORLET':
        k0 = param
        expnt = -(scale * k - k0) ** 2 / 2. * kplus
        norm = np.sqrt(scale * k[1]) * (np.pi ** (-0.25)) * np.sqrt(n)
        daughter = norm * np.exp(expnt) * kplus
        fourier_factor = (4 * np.pi) / (k0 + np.sqrt(2 + k0 ** 2))
        coi = fourier_factor / np.sqrt(2)
        dofmin = 2
    
    elif mother == 'PAUL':
        m = param
        expnt = -scale * k * kplus
        norm = np.sqrt(scale * k[1]) * (2 ** m / np.sqrt(m * np.prod(np.arange(1, (2 * m))))) * np.sqrt(n)
        daughter = norm * ((scale * k) ** m) * np.exp(expnt) * kplus
        fourier_factor = 4 * np.pi / (2 * m + 1)
        coi = fourier_factor * np.sqrt(2)
        dofmin = 2
    
    elif mother == 'DOG':
        m = param
        expnt = -(scale * k) ** 2 / 2.0
        norm = np.sqrt(scale * k[1] / gamma(m + 0.5)) * np.sqrt(n)
        daughter = -norm * (1j ** m) * ((scale * k) ** m) * np.exp(expnt)
        fourier_factor = 2 * np.pi * np.sqrt(2. / (2 * m + 1))
        coi = fourier_factor / np.sqrt(2)
        dofmin = 1
    
    else:
        raise ValueError('Wavelet mãe deve ser MORLET, PAUL ou DOG')
    
    return daughter, fourier_factor, coi, dofmin

def wave_signif(Y, dt, scale, sigtest=0, lag1=0.0, siglvl=0.95,
                dof=None, mother='MORLET', param=None, gws=None):
    """
    Calcula a significância estatística da Transformada Wavelet Contínua (CWT).

    Parâmetros:
    Y: array ou float - Dados de entrada ou variância.
    dt: float - Passo de tempo entre os pontos dos dados.
    scale: array - Escalas utilizadas na transformada wavelet.
    sigtest: int - Tipo de teste de significância (0, 1 ou 2).
    lag1: float - Coeficiente de autocorrelação lag-1.
    siglvl: float - Nível de significância (ex: 0.95 para 95%).
    dof: array ou None - Graus de liberdade.
    mother: str - Tipo de wavelet ('MORLET', 'PAUL', 'DOG').
    param: float ou None - Parâmetro específico da wavelet.
    gws: array ou None - Espectro de potência global.
    """
    n1 = len(np.atleast_1d(Y))  # Número de pontos em Y
    J1 = len(scale) - 1  # Número total de escalas
    dj = np.log2(scale[1] / scale[0])  # Espaçamento entre escalas

    # Definição da variância
    if n1 == 1:
        variance = Y  # Se Y for um valor único, assume-se que seja a variância
    else:
        variance = np.std(Y) ** 2  # Caso contrário, calcula a variância dos dados

    # Definição das wavelets e parâmetros empíricos
    if mother == 'MORLET':
        empir = ([2., -1, -1, -1])
        if param is None:
            param = 6.
            empir[1:] = ([0.776, 2.32, 0.60])
        k0 = param
        fourier_factor = (4 * np.pi) / (k0 + np.sqrt(2 + k0 ** 2))
    elif mother == 'PAUL':
        empir = ([2, -1, -1, -1])
        if param is None:
            param = 4
            empir[1:] = ([1.132, 1.17, 1.5])
        m = param
        fourier_factor = (4 * np.pi) / (2 * m + 1)
    elif mother == 'DOG':
        empir = ([1., -1, -1, -1])
        if param is None:
            param = 2.
            empir[1:] = ([3.541, 1.43, 1.4])
        elif param == 6:
            empir[1:] = ([1.966, 1.37, 0.97])
        m = param
        fourier_factor = 2 * np.pi * np.sqrt(2. / (2 * m + 1))
    else:
        raise ValueError('A função wavalet mãe deve ser: Morlet, Paul ou Dog')

    period = scale * fourier_factor  # Calcula os períodos correspondentes às escalas
    dofmin = empir[0]  # Mínimo grau de liberdade
    Cdelta = empir[1]
    gamma_fac = empir[2]
    dj0 = empir[3]
    freq = dt / period  # Frequência associada a cada período

    # Definição do espectro de potência teórico
    if gws is not None:
        fft_theor = gws
    else:
        fft_theor = (1 - lag1 ** 2) / (1 - 2 * lag1 * np.cos(freq * 2 * np.pi) + lag1 ** 2)
        fft_theor = variance * fft_theor  # Ajusta para a variância dos dados

    signif = fft_theor  # Inicializa a matriz de significância

    if dof is None:
        dof = dofmin  # Se dof não for especificado, usa o valor mínimo

    # Testes de significância
    if sigtest == 0:
        chisquare = chisquare_inv(siglvl, dof) / dof
        signif = fft_theor * chisquare  # Teste padrão de chi-quadrado
    elif sigtest == 1:
        if len(np.atleast_1d(dof)) == 1:
            dof = np.zeros(J1) + dof
        dof[dof < 1] = 1
        dof = dofmin * np.sqrt(1 + (dof * dt / gamma_fac / scale) ** 2)
        dof[dof < dofmin] = dofmin  # Garante que o dof mínimo seja respeitado
        for a1 in range(J1 + 1):
            chisquare = chisquare_inv(siglvl, dof[a1]) / dof[a1]
            signif[a1] = fft_theor[a1] * chisquare
    elif sigtest == 2:
        if len(dof) != 2:
            raise ValueError('DOF deve ser definido como [S1, S2], o intervalo de médias de escala')
        if Cdelta == -1:
            raise ValueError(' Cdelta e dj0 não estão definidos para ' + mother + ' com param = ' + str(param))
        s1, s2 = dof
        avg = np.logical_and(scale >= s1, scale < s2)
        navg = np.sum(avg.astype(int))
        if navg == 0:
            raise ValueError('Nenhuma escala válida entre ' + str(s1) + ' e ' + str(s2))
        Savg = 1. / np.sum(1. / scale[avg])
        Smid = np.exp((np.log(s1) + np.log(s2)) / 2.)
        dof = (dofmin * navg * Savg / Smid) * np.sqrt(1 + (navg * dj / dj0) ** 2)
        fft_theor = Savg * np.sum(fft_theor[avg] / scale[avg])
        chisquare = chisquare_inv(siglvl, dof) / dof
        signif = (dj * dt / Cdelta / Savg) * fft_theor * chisquare
    else:
        raise ValueError(' sigtest deve ser 0, 1 ou 2')

    return signif

def chisquare_inv(P, V):
    """Retorna o quantil P da distribuição qui-quadrado com V graus de liberdade."""
    if not 0 < P < 1:
        raise ValueError("P deve estar estritamente entre 0 e 1.")
    if V <= 0:
        raise ValueError("V deve ser positivo.")
    return chi2.ppf(P, V)
