class Stany:
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
        # czekaj na zgłoszenie gotowości przez użytkownika
        pass

    def pobierz_cwiczenie(self):
        pass

    def odtworz_animacje_instrukcje(self):
        pass

    def przechwytuj_wykonywanie_cwiczenia(self):
        pass

    def wyswietl_ocene_wykonania(self):
        pass

    def pytanie_o_powtorzenie_wybranego_cwiczenia(self):

        # czy chce powtórzyć wybrane ćwiczenie? t/N
        # N — return false
        return True

    def wybierz_cwiczenie_do_powtorzenia(self):
        pass

    def zakoncz_trening(self):
        # wyswietl raport # tutaj wywoływane wyświetlanie wykresów
        pass
