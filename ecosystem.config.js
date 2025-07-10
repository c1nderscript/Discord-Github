// Set DISCORD_GITHUB_HOME to the installation directory of the bot.
// When deploying, export the variable or edit the fallback path below.
const BASE = process.env.DISCORD_GITHUB_HOME || '/opt/discord-github';

module.exports = {
  apps: [{
    name: 'discord-github-bot',
    script: 'run.py',
    interpreter: `${BASE}/.venv/bin/python`,
    cwd: BASE,
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PATH: `${BASE}/.venv/bin:` + process.env.PATH
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
