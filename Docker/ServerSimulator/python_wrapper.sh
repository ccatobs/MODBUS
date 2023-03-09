# Start the modbus server simulator
cd modbusServerSimulator/src
python3 -u modbus_server.py &
# Start the REST API
cd ../../modbusClient/src
python3 -u mb_client_RestAPI.py --host '127.0.0.1' --port 5000 &

# Wait for any process to exit
wait

# Exit with status of process that exited first
exit $?