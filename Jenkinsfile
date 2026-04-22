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

        stage('Prepare Workspace') {
            steps {
                echo "🧹 Preparing workspace permissions..."
                sh '''
                    set -e
                    HOST_UID=$(id -u)
                    HOST_GID=$(id -g)

                    docker run --rm \
                        -u 0:0 \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            rm -rf \
                                coverage-report \
                                .pytest_cache \
                                test-results.xml \
                                integration-test-results.xml \
                                flake8-report.json \
                                pylint-report.txt \
                                pylint-files.txt \
                                coverage.xml \
                                .coverage || true

                            chown -R ${HOST_UID}:${HOST_GID} /workspace || true
                        "
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo "🧪 Running pytest suite..."
                sh '''
                    set -e
                    docker run --rm \
                        -u $(id -u):$(id -g) \
                        -e CI=true \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            pytest app/test.py -v \
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
            steps {
                echo "🔗 Running integration tests..."
                sh '''
                    set -e
                    docker run --rm \
                        -u $(id -u):$(id -g) \
                        -e CI=true \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "
                            pytest app/test.py -v \
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
                        -u $(id -u):$(id -g) \
                        -e CI=true \
                        -e PYLINTHOME=/workspace/.pylint_cache \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c '
                            flake8 . \
                                --max-line-length=120 \
                                --exclude=venv,__pycache__ \
                                --format=json > flake8-report.json || true

                            find . -name "*.py" \
                                -not -path "./.git/*" \
                                -not -path "./__pycache__/*" \
                                > pylint-files.txt

                            if [ -s pylint-files.txt ]; then
                                # Generiamo il report
                                xargs pylint --exit-zero --output-format=parseable < pylint-files.txt > pylint-report.txt
                                # Stampiamo il risultato nel log di Jenkins per visibilità immediata
                                echo "--- PYLINT REPORT START ---"
                                cat pylint-report.txt
                                echo "--- PYLINT REPORT END ---"
                            else
                                echo "No Python files found for pylint" > pylint-report.txt
                            fi
                        '
                '''

//                 // TENTATIVO DI USARE IL PLUGIN (Warnings Next Generation)
//                 script {
//                     try {
//                         recordIssues(tools: [pyLint(pattern: 'pylint-report.txt'), flake8(pattern: 'flake8-report.json')])
//                     } catch (Exception e) {
//                         echo "⚠️ Plugin 'Warnings Next Generation' non trovato. Salto la generazione dei grafici."
//                     }
//                 }
            }
        }
    }

    post {
        always {
            echo "📝 Publishing test results..."
            junit allowEmptyResults: true, testResults: '*test-results.xml'

            // QUESTA RIGA È QUELLA CHE TI FA VEDERE I RISULTATI NELLA DASHBOARD
            archiveArtifacts artifacts: 'pylint-report.txt, flake8-report.json', allowEmptyArchive: true

            sh '''
                docker image rm -f ${CI_IMAGE} 2>/dev/null || true
            '''

            cleanWs(deleteDirs: true, notFailBuild: true)
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