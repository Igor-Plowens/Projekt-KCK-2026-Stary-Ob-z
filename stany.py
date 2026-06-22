from dataclasses import dataclass
from enum import Enum, auto
import time
from functools import wraps


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
    zle_klatki: int = 0
    powtorzenia: int = 0
    wymagane_powtorzenia: int = 0
    plecy_nieproste_klatki: int = 0
    glowa_zle_klatki: int = 0
    brak_sylwetki_klatki: int = 0

    @property
    def poprawnosc(self):
        if self.wszystkie_klatki == 0:
            return 0.0
        return (self.dobre_klatki + 0.5 * self.srednie_klatki) / self.wszystkie_klatki * 100

    @property
    def successful(self):
        return self.poprawnosc >= 70 and (
                self.wymagane_powtorzenia <= 0 or self.powtorzenia >= self.wymagane_powtorzenia
        )

    def komentarze_postawy(self):
        if self.wszystkie_klatki == 0:
            return ["Nie zebrano klatek treningu."]

        plecy = self.plecy_nieproste_klatki / self.wszystkie_klatki * 100
        glowa = self.glowa_zle_klatki / self.wszystkie_klatki * 100

        return [
            "Plecy: bardzo dobrze." if plecy < 10 else "Plecy: pilnuj prostego tułowia i uginaj kolana.",
            "Głowa: bardzo dobrze." if glowa < 10 else "Głowa: nie wysuwaj jej do przodu i nie patrz stale w dół.",
        ]


class Stany:
    def __init__(self,
                 cwiczenia=None,
                 minimalny_procent_poprawnosci=70,
                 on_status_changed=None,
                 on_progress_changed=None,
                 on_result=None):
        self.cwiczenia = cwiczenia or [Cwiczenie("Podnoszenie przedmiotu z podłogi", 3)]
        self.minimalny_procent_poprawnosci = minimalny_procent_poprawnosci
        self.wyniki_cwiczen = []
        self.index_cwiczenia = -1
        self.aktualne_cwiczenie = None
        self.stan = None
        self.on_status_changed = on_status_changed
        self.on_progress_changed = on_progress_changed
        self.on_result = on_result
        self.resetuj_liczniki()

    def run(self):
        self.popros_o_przygotowanie_rekwizytow()
        while True:
            while True:
                self.pobierz_cwiczenie()
                self.odtworz_animacje_instrukcje()
                self.przechwytuj_wykonywanie_cwiczenia()
                poprawnie_wykonane = self.wyswietl_ocene_wykonania()
                if poprawnie_wykonane:
                    break

            if self.pytanie_o_powtorzenie_wybranego_cwiczenia():
                self.wybierz_cwiczenie_do_powtorzenia()
            else:
                self.zakoncz_trening()
                break

    def popros_o_przygotowanie_rekwizytow(self):
        self.stan = StanTreningu.PRZYGOTOWANIE
        self._status("Przygotuj miejsce do ćwiczeń, ustaw kamerę i stań w widocznym miejscu.")
        # czekaj na zgłoszenie gotowości przez użytkownika
        pass

    def potwierdz_gotowosc(self):
        self.pobierz_cwiczenie()
        self.odtworz_animacje_instrukcje()

    def pobierz_cwiczenie(self):
        self.index_cwiczenia += 1
        if self.index_cwiczenia >= len(self.cwiczenia):
            self.zakoncz_trening()
            return None

        self.aktualne_cwiczenie = self.cwiczenia[self.index_cwiczenia]

        return self.aktualne_cwiczenie

    def odtworz_animacje_instrukcje(self):
        if self.aktualne_cwiczenie is None:
            self.zakoncz_trening()
            return

        self.stan = StanTreningu.INSTRUKCJA

        self._status(
            f"Ćwiczenie: {self.aktualne_cwiczenie.nazwa}\n"
            f"{self.aktualne_cwiczenie.opis}\n"
            f"Czas: {self.aktualne_cwiczenie.czas_trwania} s"
        )

    def rozpocznij_cwiczenie(self):
        self.przechwytuj_wykonywanie_cwiczenia()

    def przechwytuj_wykonywanie_cwiczenia(self):
        if self.aktualne_cwiczenie is None:
            self.zakoncz_trening()
            return

        self.stan = StanTreningu.CWICZENIE
        self.resetuj_liczniki()
        self.czas_startu_cwiczenia = time.time()

        self._status("Wykonuj ćwiczenie.")

    def aktualizuj_ocene_klatki(
            self,
            wykryto_postac,
            plecy_proste,
            glowa_ok,
            gest=""
    ):
        if self.stan != StanTreningu.CWICZENIE:
            return

        self.wszystkie_klatki += 1

        if not wykryto_postac:
            self.zle_klatki += 1
            self._wyslij_postep()
            return

        liczba_poprawnych_warunkow = 0

        if plecy_proste:
            liczba_poprawnych_warunkow += 1

        if glowa_ok:
            liczba_poprawnych_warunkow += 1

        if liczba_poprawnych_warunkow == 2:
            self.dobre_klatki += 1
        elif liczba_poprawnych_warunkow == 1:
            self.srednie_klatki += 1
        else:
            self.zle_klatki += 1

        self._wyslij_postep()

        # if self._czy_czas_cwiczenia_minal():
        #     self.wyswietl_ocene_wykonania()

    def wyswietl_ocene_wykonania(self):
        self.stan = StanTreningu.OCENA

        czas_trwania = time.time() - self.czas_startu_cwiczenia

        if self.wszystkie_klatki == 0:
            procent = 0
        else:
            procent = (self.dobre_klatki / self.wszystkie_klatki) * 100

        poprawnie_wykonane = procent >= self.minimalny_procent_poprawnosci

        wynik = WynikCwiczenia(
            nazwa_cwiczenia=self.aktualne_cwiczenie.nazwa,
            czas_trwania=czas_trwania,
            dobre_klatki=self.dobre_klatki,
            srednie_klatki=self.srednie_klatki,
            wszystkie_klatki=self.wszystkie_klatki,
            poprawnosc=self.poprawnie_wykonane
        )

        self.ostatni_wynik = wynik
        self.wyniki.append(wynik)

        if poprawnie_wykonane:
            self._status(
                f"Ćwiczenie wykonane poprawnie.\n"
                f"Poprawność: {procent:.1f}%"
            )
        else:
            self._status(
                f"Ćwiczenie wymaga poprawy.\n"
                f"Poprawność: {procent:.1f}%"
            )

        if self.on_result:
            self.on_result(wynik)

        return poprawnie_wykonane

    def pytanie_o_powtorzenie_wybranego_cwiczenia(self):

        # czy chce powtórzyć wybrane ćwiczenie? t/N
        # N — return false
        return True

    def wybierz_cwiczenie_do_powtorzenia(self):
        pass

    def zakoncz_trening(self):
        # wyswietl raport # tutaj wywoływane wyświetlanie wykresów
        self.stan = StanTreningu.KONIEC
        self._status("Trening zakończony. Można wyświetlić raport.")

    def _status(self, tekst):
        if self.on_status_changed:
            self.on_status_changed(tekst)

    def _wyslij_postep(self):
        if not self.on_progress_changed:
            return

        self.on_progress_changed(
            dobre=self.dobre_klatki,
            srednie=self.srednie_klatki,
            zle=self.zle_klatki,
            wszystkie=self.wszystkie_klatki
        )

    def resetuj_liczniki(self):
        self.dobre_klatki = 0
        self.srednie_klatki = 0
        self.zle_klatki = 0
        self.wszystkie_klatki = 0
