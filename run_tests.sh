#!/bin/bash
# AIPy 测试运行脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AIPy 测试运行脚本 ===${NC}"
echo ""

# 检查是否安装了测试依赖
check_dependencies() {
    echo -e "${YELLOW}检查测试依赖...${NC}"
    if ! python -c "import pytest" 2>/dev/null; then
        echo -e "${RED}错误: pytest 未安装${NC}"
        echo "请运行: pip install -e .[test]"
        exit 1
    fi
    echo -e "${GREEN}✓ 测试依赖已安装${NC}"
    echo ""
}

# 运行测试的函数
run_tests() {
    local test_type=$1
    local test_args=$2
    
    echo -e "${YELLOW}运行 $test_type...${NC}"
    pytest $test_args
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $test_type 通过${NC}"
    else
        echo -e "${RED}✗ $test_type 失败${NC}"
        return 1
    fi
    echo ""
}

# 主菜单
show_menu() {
    echo "选择测试类型:"
    echo "1) 运行所有测试"
    echo "2) 仅运行单元测试"
    echo "3) 仅运行集成测试"
    echo "4) 运行测试并生成覆盖率报告"
    echo "5) 运行快速测试（排除慢速测试）"
    echo "6) 并行运行测试"
    echo "7) 运行特定测试文件"
    echo "8) 调试模式（显示详细输出）"
    echo "9) 退出"
    echo ""
}

# 主程序
main() {
    check_dependencies
    
    if [ $# -gt 0 ]; then
        # 如果提供了命令行参数，直接运行
        pytest "$@"
        exit $?
    fi
    
    while true; do
        show_menu
        read -p "请选择 [1-9]: " choice
        echo ""
        
        case $choice in
            1)
                run_tests "所有测试" ""
                ;;
            2)
                run_tests "单元测试" "-m unit"
                ;;
            3)
                run_tests "集成测试" "-m integration"
                ;;
            4)
                run_tests "测试（含覆盖率）" "--cov=aipyapp --cov-report=html --cov-report=term"
                echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
                ;;
            5)
                run_tests "快速测试" "-m 'not slow'"
                ;;
            6)
                run_tests "并行测试" "-n auto"
                ;;
            7)
                read -p "输入测试文件路径: " test_file
                run_tests "特定测试" "$test_file"
                ;;
            8)
                run_tests "调试模式" "-vvs --tb=long"
                ;;
            9)
                echo -e "${GREEN}退出测试运行器${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选择，请重试${NC}"
                ;;
        esac
        
        echo ""
        read -p "按回车继续..."
        clear
    done
}

# 运行主程序
main "$@"