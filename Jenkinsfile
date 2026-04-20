pipeline {
    agent {
        docker {
            image 'python:3.11'
            reuseNode true
        }
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 1, unit: 'HOURS')
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
                echo "🐍 Setting up Python environment inside Docker..."
                sh '''
                    set -e
                    python --version
                    python -m pip install --upgrade pip setuptools wheel
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running pytest suite..."
                sh '''
                    set -e
                    pytest test.py -v \
                        --tb=short \
                        --junitxml=test-results.xml \
                        --cov=. \
                        --cov-report=xml \
                        --cov-report=html:coverage-report \
                        -m "not integration"
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
                    set -e
                    pytest test.py -v \
                        -m "integration" \
                        --tb=short \
                        --junitxml=integration-test-results.xml
                '''
            }
        }

        stage('Code Quality') {
            steps {
                echo "📊 Analyzing code quality..."
                sh '''
                    set +e

                    pip install flake8 pylint

                    echo "Running flake8..."
                    flake8 . \
                        --max-line-length=120 \
                        --exclude=venv,__pycache__ \
                        --format=json > flake8-report.json

                    echo "Running pylint..."
                    find . -name "*.py" -not -path "./.git/*" -not -path "./__pycache__/*" -not -path "./venv/*" > pylint-files.txt

                    if [ -s pylint-files.txt ]; then
                        pylint $(cat pylint-files.txt) --exit-zero --output-format=parseable > pylint-report.txt
                    else
                        echo "No Python files found for pylint" > pylint-report.txt
                    fi

                    exit 0
                '''
            }
        }
    }

    post {
        always {
            echo "📝 Publishing test results..."

            junit allowEmptyResults: true, testResults: '*test-results.xml'

            script {
                if (fileExists('coverage-report/index.html')) {
                    echo "📄 Coverage HTML report generated in coverage-report/"
                } else {
                    echo "⚠️ Coverage HTML report not found."
                }
            }

            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: '__pycache__/', type: 'INCLUDE'],
                    [pattern: '.pytest_cache/', type: 'INCLUDE'],
                    [pattern: '.coverage', type: 'INCLUDE'],
                    [pattern: 'coverage.xml', type: 'INCLUDE'],
                    [pattern: 'pylint-files.txt', type: 'INCLUDE']
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