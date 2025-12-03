if not "%~1"=="" goto havecomment
set Arg1="Saving work at end of day"
echo here
goto gitstuff
:havecomment
set Arg1=%1
:gitstuff
git add .
git commit -m %Arg1%
git push
