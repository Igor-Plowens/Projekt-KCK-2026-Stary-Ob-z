Add-Type -AssemblyName System.Speech

$soundsDir = "assets\sounds"

if (!(Test-Path $soundsDir)) {
    New-Item -ItemType Directory -Path $soundsDir | Out-Null
}

$messages = @{
    "proste_plecy.wav"      = "Wyprostuj plecy"
    "glowa_do_tylu.wav"     = "Przechyl głowę do tyłu" # microsoftowe rozpoznawanie mowy jest dziwne
    "kolana_nizej.wav"      = "Ugnij kolana"
    "wolniej.wav"           = "Wolniej"
    "zatrzymaj_ruch.wav"    = "Zatrzymaj ruch"
    "dobrze.wav"            = "Dobrze"
    "popraw_pozycje.wav"    = "Popraw pozycję"
    "brak_sylwetki.wav"     = "Nie widać całej sylwetki"
    "blad_kamery.wav"       = "Problem z kamerą"
    "rozpoczecie_treningu_za_321.wav" = "Rozpoczęcie treningu za 3 ... 2 ... 1 ..."
}

foreach ($item in $messages.GetEnumerator()) {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

    # Próba wybrania polskiego głosu, jeśli jest zainstalowany w systemie
    try {
        $culture = New-Object System.Globalization.CultureInfo("pl-PL")
        $synth.SelectVoiceByHints(
            [System.Speech.Synthesis.VoiceGender]::Female,
            [System.Speech.Synthesis.VoiceAge]::Adult,
            0,
            $culture
        )
    } catch {
        Write-Host "Nie znaleziono polskiego głosu systemowego. Używam domyślnego głosu."
    }

    $synth.Rate = 0
    $synth.Volume = 100

    $outputPath = Join-Path $soundsDir $item.Key

    $synth.SetOutputToWaveFile($outputPath)
    $synth.Speak($item.Value)
    $synth.Dispose()

    Write-Host "Wygenerowano: $outputPath"
}