pipeline {
    agent any

    options {
        // Mantieni solo gli ultimi 30 build
        buildDiscarder(logRotator(numToKeepStr: '30'))
        // Timeout totale del pipeline
        timeout(time: 1, unit: 'HOURS')
    }

    environment {
        PYTHON_VERSION = '3.11'
    }

    stages {
        stage('Checkout') {
            steps {
                echo "🔄 Checking out code from branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo "🐍 Setting up Python environment..."
                sh '''
                    python3 --version
                    python3 -m pip install --user virtualenv
                    python3 -m virtualenv venv
                    . venv/bin/activate
                    python -m pip install --upgrade pip setuptools wheel
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running pytest suite..."
                sh '''
                    . venv/bin/activate
                    pytest test.py -v \
                        --tb=short \
                        --junit-xml=test-results.xml \
                        --cov=. \
                        --cov-report=xml \
                        --cov-report=html:coverage-report \
                        -m "not integration" || true
                '''
            }
        }

        stage('Integration Tests') {
            when {
                branch 'main'
            }
            steps {
                echo "🔗 Running integration tests (main branch only)..."
                sh '''
                    . venv/bin/activate
                    pytest test.py -v \
                        -m "integration" \
                        --tb=short \
                        --junit-xml=integration-test-results.xml || true
                '''
            }
        }

        stage('Code Quality') {
            steps {
                echo "📊 Analyzing code quality..."
                sh '''
                    . venv/bin/activate
                    pip install flake8 pylint 2>/dev/null || true

                    echo "Running flake8..."
                    flake8 . --max-line-length=120 --exclude=venv,__pycache__ --format=json > flake8-report.json || true

                    echo "Running pylint..."
                    pylint *.py --exit-zero --output-format=parseable > pylint-report.txt || true
                '''
            }
        }
    }

    post {
        always {
            echo "📝 Publishing test results..."

            // Pubblica i risultati dei test
            junit allowEmptyResults: true, testResults: '*test-results.xml'

            // Pubblica il report di coverage
            publishHTML([
                reportDir: 'coverage-report',
                reportFiles: 'index.html',
                reportName: 'Coverage Report'
            ])

            // Pubblica i report di linting
            recordIssues(
                enabledForFailure: true,
                tools: [
                    flake8(pattern: 'flake8-report.json')
                ]
            )

            // Pulizia
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: 'venv/', type: 'INCLUDE'],
                    [pattern: '__pycache__/', type: 'INCLUDE'],
                    [pattern: '.pytest_cache/', type: 'INCLUDE']
                ]
            )
        }

        success {
            echo "✅ Pipeline completato con successo!"
        }

        failure {
            echo "❌ Pipeline fallito! Controlla i log per i dettagli."
        }

        unstable {
            echo "⚠️ Pipeline unstable - Alcuni test sono falliti."
        }
    }
}