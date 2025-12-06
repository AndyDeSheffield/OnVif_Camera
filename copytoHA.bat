@echo off
for /f %%f in ('git diff --name-only HEAD~1 HEAD') do (
    rem Get just the extension
    set ext=%%~xf
    if /I "%ext%"==".py" (
        echo Copying %%f to R:\custom_components\onvif_camera\
        xcopy /Y %%f R:\custom_components\onvif_camera\
    )
    if /I "%ext%"==".yaml" (
        echo Copying %%f to R:\custom_components\onvif_camera\
        xcopy /Y %%f R:\custom_components\onvif_camera\
    )
)
