echo $1
python3 GUI.py $1
RES=$?
if [ $RES -eq 5 ]; then 
	./gui.sh
elif [ $RES -eq 6 ]; then
	./gui.sh /home/dardelet/Documents/PyGPUFilesProjects/Test.brd
fi
echo $?
