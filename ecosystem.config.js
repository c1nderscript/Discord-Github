module.exports = {
  apps: [{
    name: 'discord-github-bot',
    script: 'run.py',
    interpreter: '/home/cinder/Documents/D_Projects/Discord-Github/.venv/bin/python',
    cwd: '/home/cinder/Documents/D_Projects/Discord-Github',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PATH: '/home/cinder/Documents/D_Projects/Discord-Github/.venv/bin:' + process.env.PATH
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 10000,
    restart_delay: 1000
  }]
};
