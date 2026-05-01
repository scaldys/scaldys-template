echo off
prompt $S
   
:again 
   echo *************************************************************
   echo The path to the scaldys command line executable
   echo will be added to the Windows environment variable PATH.
   set /p answer=Do you want to continue (Y/N)?
   if /i "%answer:~,1%" EQU "Y" goto add_path
   if /i "%answer:~,1%" EQU "N" exit /b
   echo Please type Y for Yes or N for No
   goto again

:add_path
   setx path "%path%;%cd%\bin"

