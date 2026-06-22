from dataclasses import dataclass
from enum import Enum, auto
import time


class StanTreningu(Enum):
    PRZYGOTOWANIE = auto()
    INSTRUKCJA = auto()
    CWICZENIE = auto()
    OCENA = auto()
    KONIEC = auto()


@dataclass
class Cwiczenie:
    nazwa: str
    wymagane_powtorzenia: int = 3
    czas_trwania: int = 30
    opis: str = "Wykonaj ćwiczenie spokojnie, utrzymując prawidłową postawę."


@dataclass
class WynikCwiczenia:
    nazwa_cwiczenia: str
    czas_trwania: float
    wszystkie_klatki: int
    dobre_klatki: int
    srednie_klatki: int
    zle_klatki: int
    powtorzenia: int = 0
    wymagane_powtorzenia: int = 0
    plecy_nieproste_klatki: int = 0
    glowa_zle_klatki: int = 0
    brak_sylwetki_klatki: int = 0

    @property
    def poprawnosc(self) -> float:
        if self.wszystkie_klatki == 0:
            return 0.0
        punkty = self.dobre_klatki + 0.5 * self.srednie_klatki
        return punkty / self.wszystkie_klatki * 100.0

    @property
    def successful(self) -> bool:
        wystarczy_powtorzen = (
            self.wymagane_powtorzenia <= 0
            or self.powtorzenia >= self.wymagane_powtorzenia
        )
        return self.poprawnosc >= 70.0 and wystarczy_powtorzen

    def _procent_klatek(self, liczba_klatek: int) -> float:
        if self.wszystkie_klatki == 0:
            return 0.0
        return liczba_klatek / self.wszystkie_klatki * 100.0

    @property
    def plecy_nieproste_procent(self) -> float:
        return self._procent_klatek(self.plecy_nieproste_klatki)

    @property
    def glowa_zle_procent(self) -> float:
        return self._procent_klatek(self.glowa_zle_klatki)

    @property
    def brak_sylwetki_procent(self) -> float:
        return self._procent_klatek(self.brak_sylwetki_klatki)

    def komentarze_postawy(self):
        """Zwraca krótkie komentarze techniczne do pokazania w podsumowaniu."""
        komentarze = []

        if self.wszystkie_klatki == 0:
            return ["Nie udało się ocenić postawy, bo nie zebrano klatek treningu."]

        if self.plecy_nieproste_procent < 10:
            komentarze.append(
                "Plecy: bardzo dobrze — przez większość ruchu tułów był stabilny i prosty."
            )
        elif self.plecy_nieproste_procent < 25:
            komentarze.append(
                "Plecy: całkiem dobrze, ale pilnuj jednej linii barki–biodra podczas schodzenia po przedmiot."
            )
        else:
            komentarze.append(
                "Plecy: często wymagały poprawy — uginaj kolana mocniej i nie zaokrąglaj tułowia przy podnoszeniu."
            )

        if self.glowa_zle_procent < 10:
            komentarze.append(
                "Głowa: bardzo dobrze — głowa zwykle była cofnięta i nie opadała do przodu."
            )
        elif self.glowa_zle_procent < 25:
            komentarze.append(
                "Głowa: sporadycznie uciekała do przodu — patrz przed siebie i utrzymuj ucho nad barkiem."
            )
        else:
            komentarze.append(
                "Głowa: często była pochylona lub wysunięta — cofnij brodę i nie patrz stale w dół na przedmiot."
            )

        if self.brak_sylwetki_procent >= 15:
            komentarze.append(
                "Widoczność: kamera dość często traciła sylwetkę, więc odsuń się albo ustaw kamerę tak, aby widziała głowę, biodra i kolana."
            )

        return komentarze


class Stany:
    """
    Maszyna stanów treningu przygotowana do PyQt.
    Nie zawiera pętli while True, bo w aplikacji GUI steruje nią QTimer i przyciski.
    """

    def __init__(self, cwiczenia=None, minimalny_procent_poprawnosci=70,
                 on_status_changed=None, on_progress_changed=None, on_result=None):
        self.cwiczenia = cwiczenia or [
            Cwiczenie(
                nazwa="Podnoszenie przedmiotu z podłogi",
                wymagane_powtorzenia=3,
                czas_trwania=30,
                opis="Ugnij kolana, trzymaj plecy prosto i nie wysuwaj głowy do przodu."
            ),
            Cwiczenie(
                nazwa="Wyciąganie ciężkiego przedmiotu z bagażnika / przeciąganie po stole",
                wymagane_powtorzenia=3,
                czas_trwania=30,
                opis="Pochyl się z bioder, utrzymuj prosty kręgosłup i prowadź przedmiot blisko ciała."
            )
        ]
        self.minimalny_procent_poprawnosci = minimalny_procent_poprawnosci
        self.on_status_changed = on_status_changed
        self.on_progress_changed = on_progress_changed
        self.on_result = on_result

        self.wyniki_cwiczen = []
        self.index_cwiczenia = -1
        self.aktualne_cwiczenie = None
        self.ostatni_wynik = None
        self.stan = StanTreningu.PRZYGOTOWANIE
        self.czas_startu_cwiczenia = None
        self.resetuj_liczniki()

    @property
    def wymagane_powtorzenia(self):
        if self.aktualne_cwiczenie is None:
            return 0
        return self.aktualne_cwiczenie.wymagane_powtorzenia

    def start(self):
        self.stan = StanTreningu.PRZYGOTOWANIE
        self._status("Przygotuj miejsce do ćwiczeń, ustaw kamerę i stań w widocznym miejscu.")

    def potwierdz_gotowosc(self):
        self.pobierz_cwiczenie()
        self.odtworz_instrukcje()

    def pobierz_cwiczenie(self):
        self.index_cwiczenia += 1
        if self.index_cwiczenia >= len(self.cwiczenia):
            self.zakoncz_trening()
            return None

        self.aktualne_cwiczenie = self.cwiczenia[self.index_cwiczenia]
        return self.aktualne_cwiczenie

    def odtworz_instrukcje(self):
        if self.aktualne_cwiczenie is None:
            self.zakoncz_trening()
            return

        self.stan = StanTreningu.INSTRUKCJA
        self._status(
            f"Ćwiczenie: {self.aktualne_cwiczenie.nazwa}\n"
            f"{self.aktualne_cwiczenie.opis}\n"
            f"Powtórzenia: {self.aktualne_cwiczenie.wymagane_powtorzenia}\n"
            f"Czas: {self.aktualne_cwiczenie.czas_trwania} s"
        )

    # alias dla starej nazwy, żeby nie psuć importów
    def odtworz_animacje_instrukcje(self):
        self.odtworz_instrukcje()

    def rozpocznij_cwiczenie(self):
        if self.aktualne_cwiczenie is None:
            self.potwierdz_gotowosc()
            if self.aktualne_cwiczenie is None:
                return

        self.stan = StanTreningu.CWICZENIE
        self.resetuj_liczniki()
        self.czas_startu_cwiczenia = time.time()
        self._status("Wykonuj ćwiczenie.")
        self._wyslij_postep()

    def aktualizuj_ocene_klatki(self, wykryto_postac, plecy_proste, glowa_ok, gest=""):
        if self.stan != StanTreningu.CWICZENIE:
            return

        self.wszystkie_klatki += 1

        if not wykryto_postac:
            self.brak_sylwetki_klatki += 1
            self.zle_klatki += 1
            self._wyslij_postep()
            return

        if not plecy_proste:
            self.plecy_nieproste_klatki += 1
        if not glowa_ok:
            self.glowa_zle_klatki += 1

        liczba_poprawnych_warunkow = int(bool(plecy_proste)) + int(bool(glowa_ok))

        if liczba_poprawnych_warunkow == 2:
            self.dobre_klatki += 1
        elif liczba_poprawnych_warunkow == 1:
            self.srednie_klatki += 1
        else:
            self.zle_klatki += 1

        self._wyslij_postep()

    def zarejestruj_powtorzenie(self):
        if self.stan != StanTreningu.CWICZENIE:
            return False

        self.powtorzenia += 1
        self._wyslij_postep()
        return self.czy_wykonano_wymagane_powtorzenia()

    def czy_wykonano_wymagane_powtorzenia(self):
        return (
            self.wymagane_powtorzenia > 0
            and self.powtorzenia >= self.wymagane_powtorzenia
        )

    def wyswietl_ocene_wykonania(self):
        self.stan = StanTreningu.OCENA
        czas_trwania = 0.0 if self.czas_startu_cwiczenia is None else time.time() - self.czas_startu_cwiczenia

        wynik = WynikCwiczenia(
            nazwa_cwiczenia=self.aktualne_cwiczenie.nazwa if self.aktualne_cwiczenie else "Brak ćwiczenia",
            czas_trwania=czas_trwania,
            wszystkie_klatki=self.wszystkie_klatki,
            dobre_klatki=self.dobre_klatki,
            srednie_klatki=self.srednie_klatki,
            zle_klatki=self.zle_klatki,
            powtorzenia=self.powtorzenia,
            wymagane_powtorzenia=self.wymagane_powtorzenia,
            plecy_nieproste_klatki=self.plecy_nieproste_klatki,
            glowa_zle_klatki=self.glowa_zle_klatki,
            brak_sylwetki_klatki=self.brak_sylwetki_klatki,
        )

        self.ostatni_wynik = wynik
        self.wyniki_cwiczen.append(wynik)

        if wynik.successful:
            self._status(
                f"Ćwiczenie wykonane poprawnie.\n"
                f"Powtórzenia: {wynik.powtorzenia}/{wynik.wymagane_powtorzenia}\n"
                f"Poprawność: {wynik.poprawnosc:.1f}%"
            )
        else:
            self._status(
                f"Ćwiczenie wymaga poprawy.\n"
                f"Powtórzenia: {wynik.powtorzenia}/{wynik.wymagane_powtorzenia}\n"
                f"Poprawność: {wynik.poprawnosc:.1f}%"
            )

        if self.on_result:
            self.on_result(wynik)

        return wynik.successful

    def zakoncz_trening(self):
        self.stan = StanTreningu.KONIEC
        self._status("Trening zakończony. Można wyświetlić raport.")

    def resetuj_liczniki(self):
        self.dobre_klatki = 0
        self.srednie_klatki = 0
        self.zle_klatki = 0
        self.wszystkie_klatki = 0
        self.powtorzenia = 0
        self.plecy_nieproste_klatki = 0
        self.glowa_zle_klatki = 0
        self.brak_sylwetki_klatki = 0

    def _status(self, tekst):
        if self.on_status_changed:
            self.on_status_changed(tekst)

    def _wyslij_postep(self):
        if self.on_progress_changed:
            self.on_progress_changed(
                dobre=self.dobre_klatki,
                srednie=self.srednie_klatki,
                zle=self.zle_klatki,
                wszystkie=self.wszystkie_klatki,
                powtorzenia=self.powtorzenia,
                wymagane_powtorzenia=self.wymagane_powtorzenia,
            )

    def ustaw_cwiczenie(self, index: int):
        if 0 <= index < len(self.cwiczenia):
            self.index_cwiczenia = index - 1
            self.pobierz_cwiczenie()
            self.odtworz_instrukcje()