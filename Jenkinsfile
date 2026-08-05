pipeline {
    agent any
    options { timestamps() }

    stages {
        stage('Setup') {
            steps {
                bat 'uv sync'
                dir('mock_server/api_server') {
                    bat 'uv sync'
                }
            }
        }

        stage('Start Mock Server') {
            steps {
                powershell 'New-Item -ItemType Directory -Force -Path report/mock_server | Out-Null; Start-Process -FilePath "mock_server/api_server/.venv/Scripts/python.exe" -ArgumentList "base/flask_service.py" -WorkingDirectory "mock_server/api_server" -WindowStyle Hidden -RedirectStandardOutput "report/mock_server/server.out.log" -RedirectStandardError "report/mock_server/server.err.log"; Start-Sleep -Seconds 8'
            }
        }

        stage('Run API Tests') {
            steps {
                bat 'set PYTHONIOENCODING=utf-8 && uv run python -m pytest -q --alluredir=./report/temp ./testcase --clean-alluredir --reruns 2 --reruns-delay 1 --only-rerun ConnectionError --cov=base --cov=common --cov-report=term --cov-report=html:report/coverage --junitxml=./report/results.xml'
            }
        }

        stage('AI Analysis') {
            steps {
                bat 'set PYTHONIOENCODING=utf-8 && uv run python -m common.ai_agent'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'report/results.xml, report/coverage/**, report/ai_report.html, report/allureReport/**', allowEmptyArchive: true
        }
    }
}
