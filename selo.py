# selo.py  -- yksinkertainen SELO-laskuri (perustuu SSL-kaavoihin; odotustulos tässä
#           lasketaan tavallisella Elo-logistisella funktiolla, ei suoraan SELOn p(D)-taulukolla)
# Lähde: Suomen Shakkiliiton "Selosäännöstö" (kaavat 7.2, 7.3, 7.7, 7.8). (voit korvata
# p_of_D-funktion jos haluat täsmällisen taulukon toteutuksen).

from math import ceil

def elo_expected(Ro, Ri):
    """Elo-tyyppinen odotustulos Ro vs Ri"""
    D = Ro - Ri
    return 1.0 / (1.0 + 10.0 ** (-D / 400.0))

def Kr_for_Ro(Ro):
    """SSL 7.7: Kr riippuu Ro:sta.
       Taulukko (Ro-alue -> Kr):
         Ro >= 2050 -> 20; 1950-2049 -> 25; 1850-1949 -> 30; 1750-1849 -> 35; 1650-1749 -> 40; <=1649 -> 45
    """
    if Ro >= 2050: return 20
    if Ro >= 1950: return 25
    if Ro >= 1850: return 30
    if Ro >= 1750: return 35
    if Ro >= 1650: return 40
    return 45

def Kt_for_time(first60_minutes, Ro):
    """
    SSL 7.8: Kt riippuu peliajasta (ensim.60 siirtoa per pelaaja, minuutteina)
    ja pelaajan selosta. Tässä toteutus per taulukkoa:
     - normaali (>=90) -> Kt = 1.0
     - puolinopea (60-89) -> Kt = 0.5
     - nopea (<=59): jos Ro <= 2299 -> 0.3 else (Ro>=2300) -> 0.1
    """
    if first60_minutes >= 90: return 1.0
    if first60_minutes >= 60: return 0.5
    # <=59
    return 0.3 if Ro <= 2299 else 0.1

def new_player_selo(ris, W, N):
    """
    SSL 7.3:
      Rn = (1/N) * sum_i Ri + 400*(W - N/2) + N/10
    ris: list of vastustajien vahvuuslukuja (Ri) peleistä
    W: pelaajan pisteet kilpailussa (sum of Wi)
    N: pelimäärä
    """
    if N == 0:
        raise ValueError("N must be > 0 for a new player")
    avg_Ri = sum(ris) / N
    return round(avg_Ri + 400.0*(W - N/2.0) + N/10.0)

def established_player_selo(Ro, opponents_Ri, Ws, first60_minutes_list):
    """
    SSL 7.2:
      Rn = Ro + Kr * ( sum_i Kt_i * (Wi - Ei) + N ) / 10
    Ro: vanha Selo
    opponents_Ri: lista vastustajien Ri
    Ws: lista Wi (pelaajan pisteet per peli: 1, 0.5, 0)
    first60_minutes_list: vastaava lista peliajoista (minuutteina), käytetään Kt_for_time
    """
    N = len(opponents_Ri)
    if not (len(Ws) == N and len(first60_minutes_list) == N):
        raise ValueError("lists must be same length")
    Kr = Kr_for_Ro(Ro)
    total = 0.0
    for Ri, Wi, tmin in zip(opponents_Ri, Ws, first60_minutes_list):
        Ei = elo_expected(Ro, Ri)  # korvaa p(D)/100 jos haluat taulukon mukaisen ehdon
        Kt = Kt_for_time(tmin, Ro)
        total += Kt * (Wi - Ei)
    Rn = Ro + Kr * (total + N) / 10.0
    # pyöristetään lähimpään kokonaislukuun, puolissa ylöspäin (SSL 3.5)
    return int(Rn + 0.5)

# Esimerkki:
if __name__ == "__main__":
    Ro = 1800                                   # vakiintuneen pelaajan esimerkki
    opponents_Ri = [1750, 1820, 1900, 1700]
    Ws = [1, 0.5, 0, 1]
    times = [90, 90, 90, 90]                    # kaikki normaali aika
    print("Uusi Selo:", established_player_selo(Ro, opponents_Ri, Ws, times))

    # uuden pelaajan esimerkki
    ris = [1500, 1600, 1550]                    # uuden pelaajan esimerkki
    W = 2.0
    N = 3
    print("Uuden pelaajan laskettu Selo:", new_player_selo(ris, W, N))
