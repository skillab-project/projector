pipeline {
    agent {
        node {
            label 'dev-server'
        }
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 1, unit: 'HOURS')
    }

    environment {
        CI_IMAGE = "projector-ci:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "🔄 Checking out code from branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        stage('Build CI Image') {
            steps {
                echo "🐳 Building CI Docker image..."
                sh '''
                    set -e
                    docker build -f Dockerfile.ci -t ${CI_IMAGE} .
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running pytest suite..."
                sh '''
                    set -e
                    docker run --rm \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            pytest test.py -v \
                                --tb=short \
                                --junitxml=test-results.xml \
                                --cov=. \
                                --cov-report=xml \
                                --cov-report=html:coverage-report \
                                -m 'not integration'
                        "
                '''
            }
        }

        stage('Integration Tests') {
            when {
                branch 'main'
            }
            steps {
                echo "🔗 Running integration tests..."
                sh '''
                    set -e
                    docker run --rm \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            pytest test.py -v \
                                -m 'integration' \
                                --tb=short \
                                --junitxml=integration-test-results.xml
                        "
                '''
            }
        }

        stage('Code Quality') {
            steps {
                echo "📊 Running code quality checks..."
                sh '''
                    set +e
                    docker run --rm \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            flake8 . \
                                --max-line-length=120 \
                                --exclude=venv,__pycache__ \
                                --format=json > flake8-report.json || true

                            find . -name '*.py' \
                                -not -path './.git/*' \
                                -not -path './__pycache__/*' \
                                > pylint-files.txt

                            if [ -s pylint-files.txt ]; then
                                pylint \$(cat pylint-files.txt) --exit-zero --output-format=parseable > pylint-report.txt
                            else
                                echo 'No Python files found for pylint' > pylint-report.txt
                            fi
                        "
                    exit 0
                '''
            }
        }
    }

    post {
        always {
            echo "📝 Publishing test results..."
            junit allowEmptyResults: true, testResults: '*test-results.xml'

            sh '''
                docker image rm -f ${CI_IMAGE} 2>/dev/null || true
            '''

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