#!/bin/bash
#
# MeluXina Deployment Validation Script
# Checks if the environment is ready for AI Factory benchmarking
#

# set -e

echo "============================================================"
echo "AI Factory Benchmarking Framework - MeluXina Validation"
echo "============================================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counters
CHECKS_PASSED=0
CHECKS_FAILED=0

check_passed() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_failed() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

# 1. Check Python version
echo "1. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        check_passed "Python $PYTHON_VERSION (>= 3.8 required)"
    else
        check_failed "Python $PYTHON_VERSION (>= 3.8 required)"
    fi
else
    check_failed "Python 3 not found"
fi
echo ""

# 2. Check Apptainer/Singularity
echo "2. Checking Apptainer/Singularity..."
if command -v apptainer &> /dev/null; then
    APPTAINER_VERSION=$(apptainer --version 2>&1)
    check_passed "Apptainer found: $APPTAINER_VERSION"
elif command -v singularity &> /dev/null; then
    SINGULARITY_VERSION=$(singularity --version 2>&1)
    check_passed "Singularity found: $SINGULARITY_VERSION"
else
    check_failed "Apptainer/Singularity not found"
fi
echo ""

# 3. Check SLURM
echo "3. Checking SLURM..."
if command -v sbatch &> /dev/null; then
    SLURM_VERSION=$(sbatch --version 2>&1 | head -n 1)
    check_passed "SLURM found: $SLURM_VERSION"
    
    # Check if we can query SLURM
    if sinfo &> /dev/null; then
        check_passed "SLURM is accessible"
    else
        check_warning "SLURM command found but sinfo failed (might need to be on compute node)"
    fi
else
    check_failed "SLURM (sbatch) not found"
fi
echo ""

# 4. Check Python dependencies
echo "4. Checking Python dependencies..."
python3 << EOF
import sys
dependencies = {
    'yaml': 'PyYAML',
    'requests': 'requests'
}

all_ok = True
for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"${GREEN}✓${NC} {package} installed")
    except ImportError:
        print(f"${RED}✗${NC} {package} not installed")
        all_ok = False

sys.exit(0 if all_ok else 1)
EOF

if [ $? -eq 0 ]; then
    ((CHECKS_PASSED += 2))
else
    ((CHECKS_FAILED += 2))
fi
echo ""

# 5. Check directory structure
echo "5. Checking directory structure..."
REQUIRED_DIRS=("src" "apptainer_recipes" "scripts" "design")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_passed "Directory '$dir' exists"
    else
        check_failed "Directory '$dir' not found"
    fi
done
echo ""

# 6. Check required files
echo "6. Checking required files..."
REQUIRED_FILES=(
    "recipe.yml"
    "requirements.txt"
    "src/main.py"
    "scripts/run_benchmark.sh"
)
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_passed "File '$file' exists"
    else
        check_failed "File '$file' not found"
    fi
done
echo ""

# 7. Check storage paths
echo "7. Checking storage paths..."
if [ ! -z "$PROJECT" ]; then
    check_passed "PROJECT environment variable set: $PROJECT"
    
    if [ -d "$PROJECT" ]; then
        check_passed "PROJECT directory accessible"
    else
        check_failed "PROJECT directory not accessible"
    fi
else
    check_warning "PROJECT environment variable not set (required for MeluXina)"
fi
echo ""

# 8. Check GPU availability (optional)
echo "8. Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | wc -l)
    if [ "$GPU_COUNT" -gt 0 ]; then
        check_passed "GPU(s) available: $GPU_COUNT"
    else
        check_warning "nvidia-smi found but no GPUs detected"
    fi
else
    check_warning "nvidia-smi not found (GPUs optional but recommended for LLM benchmarking)"
fi
echo ""

# 9. Test basic Python imports
echo "9. Testing framework imports..."
python3 << EOF
import sys
sys.path.insert(0, 'src')
try:
    from middleware.interface import MiddlewareInterface
    from client.client import BenchmarkClient
    from server.server import ServiceManager
    from monitor.monitor import Monitor
    from reporter.reporter import BenchmarkReporter
    from logger.logger import BenchmarkLogger
    print("${GREEN}✓${NC} All framework components can be imported")
    sys.exit(0)
except ImportError as e:
    print(f"${RED}✗${NC} Import error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    ((CHECKS_PASSED++))
else
    ((CHECKS_FAILED++))
fi
echo ""

# 10. Check write permissions
echo "10. Checking write permissions..."
TEST_DIRS=("logs" "reports")
for dir in "${TEST_DIRS[@]}"; do
    mkdir -p "$dir" 2>/dev/null
    if [ -w "$dir" ]; then
        check_passed "Write access to '$dir/' directory"
    else
        check_failed "No write access to '$dir/' directory"
    fi
done
echo ""

# Summary
echo "============================================================"
echo "VALIDATION SUMMARY"
echo "============================================================"
echo -e "${GREEN}Passed: $CHECKS_PASSED${NC}"
echo -e "${RED}Failed: $CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Environment is ready for benchmarking!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Edit recipe.yml to configure your benchmarks"
    echo "2. Build containers: bash scripts/build_containers.sh"
    echo "3. Submit job: sbatch scripts/run_benchmark.sh"
    exit 0
else
    echo -e "${RED}✗ Please fix the failed checks before proceeding${NC}"
    echo ""
    echo "To fix issues:"
    echo "1. Load required modules: module load Python Apptainer"
    echo "2. Install dependencies: pip install -r requirements.txt"
    echo "3. Ensure you're in the correct project directory"
    exit 1
fi
