#!/bin/bash
cd "$(dirname "$0")"

./stop_services.sh
sleep 2
./start_services.sh
