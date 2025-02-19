# Hardware Monitor

A real-time system monitoring tool that tracks CPU, RAM, disk usage, and network performance. The application provides both a command-line interface and a web-based dashboard for visualizing system metrics.

## Features

- Real-time system metrics monitoring
- Web-based dashboard with pie charts
- Push notifications for critical alerts (via Pushbullet)
- WebSocket-based real-time updates
- Monitoring of:
  - CPU usage
  - RAM utilization
  - Disk usage and I/O
  - Network latency and throughput
  - System temperature (where available)
  - Battery status (for laptops)

## Prerequisites

- Python 3.12+
- Redis
- Docker (optional, for running Redis)
- Pushbullet API key (optional, for notifications)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd hardwareMonitor
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\activate
```

3. Install required packages:
```bash
pip install django
pip install channels
pip install channels-redis
pip install daphne
pip install psutil
pip install pushbullet.py
```

4. Start Redis server (choose one method):

Using Docker:
```bash
sudo docker run -p 6379:6379 -d redis
```

Or using native Redis:
```bash
redis-server
```

5. Apply Django migrations:
```bash
python manage.py migrate
```

## Configuration

1. Set up your Pushbullet API key (optional):
   - Create an account at https://www.pushbullet.com
   - Get your API key from Account Settings
   - Replace `PUSHBULLET_API_KEY` in `main.py` with your key

2. Configure monitoring thresholds (optional):
   - Edit the thresholds dictionary in `main.py` to adjust alert levels
   - Default thresholds are set for common use cases

## Usage

1. Start the Django development server:
```bash
python manage.py runserver
```

2. In a separate terminal, run the monitoring script:
```bash
python hardware_monitor.py
```

3. Access the web dashboard:
   - Open http://localhost:8000 in your web browser
   - The dashboard will automatically update with real-time system metrics

## Project Structure

```
hardwareMonitor/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── fault_detection/
│   ├── consumers.py
│   ├── routing.py
│   └── views.py
├── templates/
│   └── monitor.html
├── hardware_monitor.py
└── manage.py
```

## Alert Thresholds

Default thresholds for alerts:

- CPU Usage:
  - Warning: 70%
  - Critical: 90%
- RAM Usage:
  - Warning: 70%
  - Critical: 90%
- Disk Usage:
  - Warning: 80%
  - Critical: 90%
- Temperature:
  - Warning: 70°C
  - Critical: 85°C
- Network Latency:
  - Warning: 100ms
  - Critical: 200ms
- Battery Level:
  - Warning: 15%
  - Critical: 10%

## Troubleshooting

1. Redis Connection Issues:
   ```bash
   # Test Redis connection
   redis-cli ping
   ```

2. WebSocket Connection:
   - Check browser console for WebSocket errors
   - Ensure Redis is running
   - Verify CHANNEL_LAYERS setting in Django settings.py

## Acknowledgments

- Built with Django and Channels
- Uses psutil for system monitoring
- Chart.js for data visualization
- Pushbullet for notifications