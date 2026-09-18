# FFmpeg-NDI-for-win-x64

Сборка FFmpeg **9.0.1** (ffmpeg / ffprobe / ffplay) для **Windows x64** с поддержкой NDI
(NewTek NDI 6 SDK) — инпут- и аутпут-устройства `libndi_newtek`.

NDI — non-free, поэтому собирается с `--enable-nonfree` и **не подлежит распространению**
(см. https://docs.ndi.video/all/faq/sdk/using-ffmpeg-with-ndi).

## Как это работает (GitHub Actions)

Workflow: `.github/workflows/build-ffmpeg-ndi-win-x64.yml` (запускается на push в `main`
и вручную через Actions → Run workflow).

1. **NDI SDK** берётся из установщика `sdk/NDI6-SDK.exe`, закоммиченного в репозиторий,
   и распаковывается 7-Zip **без установки** (официальный download.ndi.tv отдаёт 403).
2. MSYS2 (ucrt64) + mingw-w64 cross toolchain: `mingw-w64-ucrt-x86_64-{gcc,nasm,sdl2,zlib,pkgconf}`.
3. Клонируется FFmpeg `n9.0.1`, накладывается `ndi-patch/ffmpeg_9.0-add_ndi.patch`
   (+ `libndi_newtek_{common,dec,enc}`), SDK кладётся в дерево сборки
   (`Processing.NDI.Lib.h` + `libndi.dll.a` для `-lndi`).
4. `configure --enable-nonfree --enable-libndi_newtek --extra-ldflags=-static ...`,
   `make -j2`. `-static` в ldflags зашивает GCC-рантайм, zlib и SDL2 прямо в exe
   (для статического линка ставится plain-пакет `mingw-w64-ucrt-x86_64-SDL2` —
   он содержит `libSDL2.a`; `sdl2-compat` даёт только импортную библиотеку).
   NDI остаётся dynamic: вендор распространяет NDI только как shared-библиотеку,
   статической версии не существует.
5. Smoke-тесты: `-devices` содержит `libndi_newtek`, импорт `Processing.NDI.Lib.x64.dll`
   в ffmpeg.exe, и **реальный NDI-лоупбек**: lavfi-источник транслируется в
   `hermes_ci_source`, ffmpeg его ловит, декодирует ≥25 кадров.
6. Результат: артефакт `ffmpeg-9.0.1-ndi-win-x64.zip` (3 exe +
   `Processing.NDI.Lib.x64.dll` + Version.txt + README); комплект DLL
   определяется динамически из PE-таблиц импортов exe (системные DLL
   отбрасываются), а не хардкод-списком. При ручном запуске дополнительно
   публикуется GitHub Release (prerelease).

## Запуск

- push в `main` → автозапуск; результат в **Actions → Run → Artifacts**
  (`ffmpeg-9.0.1-ndi-win-x64`) и в **Releases** (только для ручных запусков).
- Ручной запуск: GitHub → Actions → `build-ffmpeg-ndi-win-x64` → Run workflow.

## Использование

NDI-устройства доступны как `-f libndi_newtek`:

```bat
:: список источников
ffmpeg -f libndi_newtek -find_sources 1 -i dummy

:: приём NDI-источника в файл
ffmpeg -i "ИМЯ_ИСТОЧНИКА" -c copy out.mkv

:: передача (видео UYVY/BGRA/BGR0/RGBA/RGB0, audio pcm_s16le)
ffmpeg -re -i input.mp4 -c:v wrapped_avframe -pix_fmt uyvy422 -c:a pcm_s16le -f libndi_newtek MY_SOURCE
```

NDI DLL лежат рядом с бинарниками в архиве — распаковывайте целиком в одну папку.

## Состав репозитория

```
sdk/NDI6-SDK.exe                      # установщик NDI 6 SDK (источник SDK для CI)
ndi-patch/ffmpeg_9.0-add_ndi.patch    # патч NDI для FFmpeg 9.0/9.0.1
ndi-patch/libavdevice/libndi_newtek_* # код устройств (из 8Kloud/ffmpeg-ndi-patch)
.github/workflows/build-ffmpeg-ndi-win-x64.yml
```

NDI-патч — fork 8Kloud/ffmpeg-ndi-patch (Tytan652), адаптированный под FFmpeg 9.0.1 / NDI 6.3.x.
