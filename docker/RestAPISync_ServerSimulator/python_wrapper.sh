# Start the modbus server simulator
cd modbusServerSimulator/src/
python3 -u modbus_server.py &
# Start the REST API
cd ../..
python3 -u RestAPISync/mb_client_RestAPISync.py --host $HOST --port $PORT &

# Wait for any process to exit
wait

# Exit with status of process that exited first
exit $?