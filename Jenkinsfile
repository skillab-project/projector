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
        GITHUB_STATUS_CREDENTIALS_ID = "1efb02bc-566c-433b-9e76-577fcb07cf5b"
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
                                test-report \
                                coverage-report \
                                mutation-report \
                                quality-dashboard \
                                mutants \
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
                        -e PYTHONPATH=/workspace \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c '
                            COVERAGE_GATE=$(python tools/quality_gates.py coverage)

                            pytest app/test.py -v \
                                --tb=short \
                                --junitxml=test-results.xml \
                                --cov=app \
                                --cov-branch \
                                --cov-report=xml \
                                --cov-report=html:coverage-report \
                                --cov-fail-under="${COVERAGE_GATE}" \
                                -m "not integration"
                        '
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
                        -e PYTHONPATH=/workspace \
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

        stage('Mutation Testing') {
            steps {
                echo "🧬 Running mutation test analysis..."
                sh '''
                    set +e
                    docker run --rm \
                        -u $(id -u):$(id -g) \
                        -e CI=true \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c '
                            set +e

                            mutmut --version

                            mutmut run --max-children 4
                            MUTMUT_EXIT=$?
                            echo "mutmut exit code: ${MUTMUT_EXIT}"

                            python tools/mutation_report.py || true
                            mutmut export-cicd-stats || true

                            echo "--- MUTATION REPORT FILES START ---"
                            find mutation-report -maxdepth 2 -type f -print || true
                            echo "--- MUTATION REPORT FILES END ---"

                            echo "--- MUTATION TEST SUMMARY START ---"
                            if [ -f mutants/mutmut-cicd-stats.json ]; then
                                cat mutants/mutmut-cicd-stats.json
                            else
                                echo "No mutation stats generated"
                            fi
                            echo "--- MUTATION TEST SUMMARY END ---"

                            # Quality gate futuro, intenzionalmente disabilitato mentre fissiamo la baseline.
                            # Soglie suggerite:
                            # 1. score >= 55 dopo aver coperto i cluster principali di survivor.
                            # 2. score >= 65 quando sectoral/loader avranno test piu forti.
                            # 3. score >= 70 solo sul profilo mutmut selezionato, non su tutta l'app.
                            #
                            # python - <<'"'"'PY'"'"'
                            # import json
                            # from pathlib import Path
                            #
                            # stats_path = Path("mutants/mutmut-cicd-stats.json")
                            # if not stats_path.exists():
                            #     raise SystemExit("Mutation stats file missing")
                            #
                            # stats = json.loads(stats_path.read_text())
                            # killed = stats.get("killed", 0)
                            # survived = stats.get("survived", 0)
                            # effective = killed + survived
                            # score = (killed / effective * 100) if effective else 0.0
                            #
                            # threshold = 55.0
                            # if score < threshold:
                            #     raise SystemExit(
                            #         f"Mutation score {score:.1f}% is below threshold {threshold:.1f}%"
                            #     )
                            # PY

                            exit 0
                        '
                '''
            }
        }
    }

    post {
        always {
            echo "📝 Publishing test results..."
            junit allowEmptyResults: true, testResults: '*test-results.xml'

            sh '''
                set +e
                if docker image inspect ${CI_IMAGE} >/dev/null 2>&1; then
                    docker run --rm \
                        -u $(id -u):$(id -g) \
                        -e BUILD_URL="${BUILD_URL}" \
                        -e GIT_COMMIT="${GIT_COMMIT}" \
                        -e BRANCH_NAME="${BRANCH_NAME}" \
                        -e CHANGE_ID="${CHANGE_ID}" \
                        -e CHANGE_BRANCH="${CHANGE_BRANCH}" \
                        -e CHANGE_TARGET="${CHANGE_TARGET}" \
                        -e JOB_NAME="${JOB_NAME}" \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace \
                        ${CI_IMAGE} \
                        sh -c "python tools/test_report.py && python tools/quality_dashboard.py" || true
                else
                    echo "CI image ${CI_IMAGE} not available; skipping quality dashboard generation."
                fi
            '''

            // QUESTA RIGA È QUELLA CHE TI FA VEDERE I RISULTATI NELLA DASHBOARD
            archiveArtifacts artifacts: 'quality-dashboard/**, test-report/**, coverage.xml, coverage-report/**, pylint-report.txt, flake8-report.json, mutation-report/**, mutants/mutmut-cicd-stats.json', allowEmptyArchive: true

            script {
                try {
                    withCredentials([usernamePassword(credentialsId: env.GITHUB_STATUS_CREDENTIALS_ID, usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_TOKEN')]) {
                        sh '''
                            set +e
                            if docker image inspect ${CI_IMAGE} >/dev/null 2>&1; then
                                docker run --rm \
                                    -u $(id -u):$(id -g) \
                                    -e BUILD_URL="${BUILD_URL}" \
                                    -e GIT_COMMIT="${GIT_COMMIT}" \
                                    -e BRANCH_NAME="${BRANCH_NAME}" \
                                    -e CHANGE_ID="${CHANGE_ID}" \
                                    -e CHANGE_BRANCH="${CHANGE_BRANCH}" \
                                    -e CHANGE_TARGET="${CHANGE_TARGET}" \
                                    -e JOB_NAME="${JOB_NAME}" \
                                    -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
                                    -v "$WORKSPACE:/workspace" \
                                    -w /workspace \
                                    ${CI_IMAGE} \
                                    sh -c "python tools/github_statuses.py" || true
                            else
                                echo "CI image ${CI_IMAGE} not available; skipping GitHub commit statuses."
                            fi
                        '''
                    }
                } catch (Exception e) {
                    echo "GitHub commit statuses skipped: ${e.getMessage()}"
                }
            }

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
