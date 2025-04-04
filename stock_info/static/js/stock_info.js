// 页面元素
const stockCodeInput = document.getElementById('stockCode');
const searchBtn = document.getElementById('searchBtn');
const stockInfoDiv = document.getElementById('stockInfoDiv');
const loadingDiv = document.getElementById('loadingDiv');
const errorDiv = document.getElementById('errorDiv');
const stockTitle = document.getElementById('stockTitle');
const financialData = document.getElementById('financialData');
let financialChart = null;

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    // 绑定搜索按钮点击事件
    searchBtn.addEventListener('click', searchStock);
    
    // 绑定输入框回车事件
    stockCodeInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchStock();
        }
    });

    // 检查URL参数，如果有股票代码参数则自动查询
    const urlParams = new URLSearchParams(window.location.search);
    const codeParam = urlParams.get('code');
    
    if (codeParam) {
        stockCodeInput.value = codeParam;
        searchStock(); // 自动触发查询
    }
});

// 搜索股票
function searchStock() {
    const stockCode = stockCodeInput.value.trim();
    
    // 验证股票代码
    if (!stockCode) {
        showError('请输入股票代码');
        return;
    }
    
    if (!/^\d{6}$/.test(stockCode)) {
        showError('股票代码必须是6位数字');
        return;
    }
    
    // 隐藏错误提示和股票信息
    errorDiv.classList.add('d-none');
    stockInfoDiv.classList.add('d-none');
    
    // 显示加载提示
    loadingDiv.classList.remove('d-none');
    
    // 调用API获取股票财务数据
    fetch(`/api/stock_finance?code=${stockCode}`)
        .then(response => response.json())
        .then(data => {
            // 隐藏加载提示
            loadingDiv.classList.add('d-none');
            
            // 检查是否有错误
            if (data.error) {
                showError(data.error);
                return;
            }
            
            // 显示股票信息
            displayStockInfo(data);
        })
        .catch(error => {
            // 隐藏加载提示
            loadingDiv.classList.add('d-none');
            
            // 显示错误信息
            showError('获取数据失败，请稍后再试');
            console.error('Error:', error);
        });
}

// 显示错误信息
function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

// 显示股票信息
function displayStockInfo(data) {
    // 修正数据结构访问方式
    const stockData = data.data || data;
    
    // 显示股票标题
    stockTitle.textContent = `${stockData.name}(${stockData.code}) - 财务数据`;
    
    // 清空财务数据表格
    financialData.innerHTML = '';
    
    // 填充财务数据表格
    const financialDataList = stockData.financial_data;
    if (financialDataList && financialDataList.length > 0) {
        financialDataList.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.报告期}</td>
                <td>${item.负债率 !== null ? item.负债率.toFixed(2) : '-'}</td>
                <td>${item.净利率 !== null ? item.净利率.toFixed(2) : '-'}</td>
                <td>${item.毛利率 !== null ? item.毛利率.toFixed(2) : '-'}</td>
            `;
            financialData.appendChild(row);
        });
        
        // 创建图表
        createChart(financialDataList);
    } else {
        // 无数据时显示提示
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="text-center">暂无财务数据</td>';
        financialData.appendChild(row);
    }
    
    // 显示股票信息区域
    stockInfoDiv.classList.remove('d-none');
}

// 创建财务数据图表
function createChart(data) {
    // 获取图表容器
    const ctx = document.getElementById('financialChart').getContext('2d');
    
    // 销毁旧图表（如果存在）
    if (financialChart) {
        financialChart.destroy();
    }
    
    // 提取数据
    const periods = data.map(item => item.报告期);
    const debtRatios = data.map(item => item.负债率);
    const netProfitRatios = data.map(item => item.净利率);
    const grossProfitRatios = data.map(item => item.毛利率);
    
    // 创建新图表
    financialChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: periods,
            datasets: [
                {
                    label: '负债率(%)',
                    data: debtRatios,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                },
                {
                    label: '净利率(%)',
                    data: netProfitRatios,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.1
                },
                {
                    label: '毛利率(%)',
                    data: grossProfitRatios,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 3, // 设置宽高比为3:1（宽度是高度的3倍）
            plugins: {
                title: {
                    display: true,
                    text: '财务指标趋势'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '百分比(%)'
                    }
                }
            }
        }
    });
}