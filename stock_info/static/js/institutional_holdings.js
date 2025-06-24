// 机构持股页面JavaScript

// 全局变量
let currentCategory = 'all';
let currentReportDate = null;
let availableReportDates = [];
let holdingsData = {};
let stockDetailModal = null;
let charts = {};
let loadingStates = {};
let debounceTimers = {};
let dataCache = {};
let performanceData = {
    loadTimes: [],
    errorCount: 0,
    lastUpdate: null
};

// 性能监控
function trackPerformance(category, startTime, success) {
    const loadTime = Date.now() - startTime;
    performanceData.loadTimes.push({
        category: category,
        time: loadTime,
        timestamp: new Date().toISOString()
    });
    
    if (!success) {
        performanceData.errorCount++;
    }
    
    performanceData.lastUpdate = new Date().toISOString();
    
    // 保持最近50次记录
    if (performanceData.loadTimes.length > 50) {
        performanceData.loadTimes = performanceData.loadTimes.slice(-50);
    }
    
    console.log(`[性能] ${category} 加载耗时: ${loadTime}ms, 成功: ${success}`);
}

function showPerformanceIndicator(message) {
    const indicator = document.getElementById('performanceIndicator');
    const textElement = document.getElementById('performanceText');
    if (indicator && textElement) {
        textElement.textContent = message;
        indicator.style.display = 'block';
    }
}

function hidePerformanceIndicator() {
    const indicator = document.getElementById('performanceIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

function updatePerformanceMetrics(isFromCache = false) {
    performanceMetrics.requestCount++;
    if (isFromCache) {
        performanceMetrics.cacheHits++;
    }
    
    const cacheHitRate = (performanceMetrics.cacheHits / performanceMetrics.requestCount * 100).toFixed(1);
    console.log(`性能统计 - 请求总数: ${performanceMetrics.requestCount}, 缓存命中率: ${cacheHitRate}%`);
}

// 获取类别显示名称
function getCategoryDisplayName(category) {
    const categoryNames = {
        'all': '全部机构',
        'fund': '基金',
        'insurance': '保险',
        'qfii': 'QFII',
        'social-security': '社保'
    };
    return categoryNames[category] || category;
}

// 格式化报告期显示
function formatReportDate(dateStr) {
    const str = dateStr.toString();
    if (str.length === 8) {
        const year = str.substring(0, 4);
        const month = str.substring(4, 6);
        const day = str.substring(6, 8);
        
        // 根据月日判断季度
        if (month === '03' && day === '31') {
            return `${year}Q1`;
        } else if (month === '06' && day === '30') {
            return `${year}Q2`;
        } else if (month === '09' && day === '30') {
            return `${year}Q3`;
        } else if (month === '12' && day === '31') {
            return `${year}Q4`;
        }
    }
    return dateStr;
}

// 加载可用报告期
async function loadAvailableReportDates() {
    try {
        const response = await fetch('/api/institutional_holdings/report_dates');
        const result = await response.json();
        
        if (result.status === 'success') {
            availableReportDates = result.data;
            currentReportDate = availableReportDates[0]; // 默认选择最新报告期
            console.log('可用报告期:', availableReportDates);
            return true;
        } else {
            console.error('获取报告期失败:', result.message);
            return false;
        }
    } catch (error) {
        console.error('加载报告期出错:', error);
        return false;
    }
}

// 生成报告期标签
function generateReportDateTabs(category) {
    const tabsContainer = document.getElementById(`${category}-report-tabs`);
    if (!tabsContainer || !availableReportDates.length) {
        return;
    }
    
    tabsContainer.innerHTML = '';
    
    availableReportDates.forEach((date, index) => {
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.role = 'presentation';
        
        const button = document.createElement('button');
        button.className = `nav-link ${index === 0 ? 'active' : ''}`;
        button.id = `${category}-${date}-tab`;
        button.setAttribute('data-bs-toggle', 'pill');
        button.setAttribute('data-bs-target', `#${category}-${date}`);
        button.type = 'button';
        button.role = 'tab';
        button.textContent = formatReportDate(date);
        
        // 添加点击事件
        button.addEventListener('click', () => {
            currentReportDate = date;
            
            // 立即清理错误状态
            const errorElement = document.getElementById(`${category}-error`);
            if (errorElement) {
                errorElement.style.display = 'none';
                errorElement.textContent = '';
            }
            
            loadCategoryData(category, date);
        });
        
        li.appendChild(button);
        tabsContainer.appendChild(li);
    });
}

// 个股查询功能
function queryStockDetail() {
    const stockCode = document.getElementById('stockCodeInput').value.trim();
    
    if (!stockCode) {
        alert('请输入股票代码');
        return;
    }
    
    // 显示模态框
    if (!stockDetailModal) {
        stockDetailModal = new bootstrap.Modal(document.getElementById('stockDetailModal'));
    }
    stockDetailModal.show();
    
    // 重置模态框内容
    document.getElementById('stockDetailModalLabel').textContent = `${stockCode} 持股详情`;
    document.getElementById('stockDetailContent').innerHTML = `
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在加载股票详细信息...</p>
        </div>
    `;
    
    // 获取股票详细持股信息
    fetch(`/api/stock_holdings_detail/${stockCode}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayStockDetail(data.data);
            } else {
                document.getElementById('stockDetailContent').innerHTML = `
                    <div class="alert alert-warning" role="alert">
                        <h4 class="alert-heading">未找到数据</h4>
                        <p>未找到股票代码 ${stockCode} 的机构持股信息。</p>
                        <hr>
                        <p class="mb-0">请检查股票代码是否正确，或该股票可能没有机构持股数据。</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('获取股票详细信息失败:', error);
            document.getElementById('stockDetailContent').innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h4 class="alert-heading">加载失败</h4>
                    <p>获取股票详细信息时发生错误。</p>
                    <hr>
                    <p class="mb-0">错误信息: ${error.message}</p>
                </div>
            `;
        });
}

// 显示股票详细持股信息
function displayStockDetail(data) {
    if (!data || !data.stock_info) {
        document.getElementById('stockDetailContent').innerHTML = `
            <div class="alert alert-warning" role="alert">
                数据格式错误或无有效数据
            </div>
        `;
        return;
    }
    
    const stockInfo = data.stock_info;
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h4>${stockInfo.stock_name} (${stockInfo.stock_code})</h4>
            </div>
        </div>
    `;
    
    // 检查是否有数据
    if (!data.by_institution_type || Object.keys(data.by_institution_type).length === 0) {
        html += `
            <div class="alert alert-info" role="alert">
                该股票暂无机构持股数据记录
            </div>
        `;
        document.getElementById('stockDetailContent').innerHTML = html;
        return;
    }
    
    // 创建图表容器
    html += `
        <div class="row">
            <div class="col-12">
                <h5>机构持股比例变化趋势</h5>
                <div class="chart-container mb-4" style="height: 400px;">
                    <canvas id="stockDetailChart"></canvas>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-12">
                <h5>各机构类型持股分布</h5>
                <div class="chart-container" style="height: 300px;">
                    <canvas id="stockDetailPieChart"></canvas>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('stockDetailContent').innerHTML = html;
    
    // 创建趋势图表
    createStockDetailTrendChart(data.by_institution_type);
    
    // 创建饼图
    createStockDetailPieChart(data.by_institution_type);
}

// 创建个股详情趋势图表
function createStockDetailTrendChart(institutionData) {
    const ctx = document.getElementById('stockDetailChart');
    if (!ctx) return;
    
    // 销毁已存在的图表
    if (window.stockDetailChart && typeof window.stockDetailChart.destroy === 'function') {
        window.stockDetailChart.destroy();
    }
    
    // 准备数据
    const datasets = [];
    const colors = {
        '基金': '#FF6384',
        '保险': '#36A2EB',
        'QFII': '#FFCE56',
        '社保': '#4BC0C0',
        '券商': '#9966FF',
        '信托': '#FF9F40',
        '其他': '#C9CBCF'
    };
    
    // 定义所有可能的机构类型（与后端返回的格式一致）
    const allInstitutionTypes = ['基金', '保险', 'QFII', '社保'];
    
    let allDates = new Set();
    
    // 收集所有日期
    Object.values(institutionData).forEach(periods => {
        periods.forEach(period => {
            allDates.add(period.report_date);
        });
    });
    
    const sortedDates = Array.from(allDates).sort();
    
    // 为所有机构类型创建数据集，包括没有数据的类型
    allInstitutionTypes.forEach(instType => {
        const periods = institutionData[instType] || [];
        const data = sortedDates.map(date => {
            const period = periods.find(p => p.report_date === date);
            return period ? parseFloat(period.holding_ratio) : 0; // 改为0而不是null
        });
        
        datasets.push({
            label: instType,
            data: data,
            borderColor: colors[instType] || '#' + Math.floor(Math.random()*16777215).toString(16),
            backgroundColor: (colors[instType] || '#' + Math.floor(Math.random()*16777215).toString(16)) + '20',
            fill: false,
            tension: 0.1,
            spanGaps: false // 改为false，因为现在用0填充而不是null
        });
    });
    
    // 添加实际存在但不在预定义列表中的机构类型
    Object.keys(institutionData).forEach(instType => {
        if (!allInstitutionTypes.includes(instType)) {
            const periods = institutionData[instType];
            const data = sortedDates.map(date => {
                const period = periods.find(p => p.report_date === date);
                return period ? parseFloat(period.holding_ratio) : 0;
            });
            
            datasets.push({
                 label: instType,
                 data: data,
                 borderColor: colors[instType] || '#' + Math.floor(Math.random()*16777215).toString(16),
                 backgroundColor: (colors[instType] || '#' + Math.floor(Math.random()*16777215).toString(16)) + '20',
                 fill: false,
                 tension: 0.1,
                 spanGaps: false
             });
         }
     });
    
    window.stockDetailChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '各机构类型持股比例变化趋势'
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '持股比例(%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '报告期'
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// 创建个股详情饼图
function createStockDetailPieChart(institutionData) {
    const ctx = document.getElementById('stockDetailPieChart');
    if (!ctx) return;
    
    // 销毁已存在的图表
    if (window.stockDetailPieChart && typeof window.stockDetailPieChart.destroy === 'function') {
        window.stockDetailPieChart.destroy();
    }
    
    // 找到全局最新报告期（数字格式比较）
    let globalLatestDate = 0;
    Object.values(institutionData).forEach(periods => {
        periods.forEach(period => {
            const currentDate = parseInt(period.report_date);
            if (currentDate > globalLatestDate) {
                globalLatestDate = currentDate;
            }
        });
    });
    
    // 只显示最新期有数据的机构类型
    const latestData = {};
    if (globalLatestDate > 0) {
        Object.keys(institutionData).forEach(instType => {
            const periods = institutionData[instType];
            const latestPeriod = periods.find(period => {
                return parseInt(period.report_date) === globalLatestDate;
            });
            
            if (latestPeriod) {
                latestData[instType] = parseFloat(latestPeriod.holding_ratio);
            }
        });
    }
    
    const labels = Object.keys(latestData);
    const data = Object.values(latestData);
    const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'];
    
    window.stockDetailPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '最新期各机构类型持股分布'
                },
                legend: {
                    display: true,
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value}% (占比${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initPage();
    
    // 预加载所有类别数据
    preloadAllData();
    
    // 绑定回车键查询
    const stockCodeInput = document.getElementById('stockCodeInput');
    if (stockCodeInput) {
        stockCodeInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                queryStockDetail();
            }
        });
    }
});

// 预加载所有类别数据
function preloadAllData() {
    const categories = ['all', 'fund', 'insurance', 'qfii', 'social-security'];
    
    // 延迟预加载，避免阻塞主要内容
    setTimeout(() => {
        categories.forEach((category, index) => {
            if (category !== 'all') {
                // 错开请求时间，避免并发过多
                setTimeout(() => {
                    loadCategoryData(category, null, true); // 第三个参数true表示静默加载
                }, index * 200);
            }
        });
    }, 1000);
}

// 初始化标签页事件
function initTabEvents() {
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function (event) {
            const targetId = event.target.getAttribute('data-bs-target');
            const category = targetId.replace('#', '');
            
            console.log(`切换到标签页: ${category}`);
            currentCategory = category;
            
            // 立即清理错误状态
            const errorElement = document.getElementById(`${category}-error`);
            if (errorElement) {
                errorElement.style.display = 'none';
                errorElement.textContent = '';
            }
            
            // 生成报告期标签
            generateReportDateTabs(category);
            
            // 加载对应类别的数据
            loadCategoryData(category);
        });
    });
}

// 初始化页面
async function initPage() {
    try {
        // 首先加载可用报告期
        const success = await loadAvailableReportDates();
        if (!success) {
            console.error('无法加载报告期，使用默认设置');
        }
        
        // 初始化标签页事件
        initTabEvents();
        
        // 为默认类别生成报告期标签
        generateReportDateTabs('all');
        
        // 默认加载第一个标签页的数据
        loadCategoryData('all');
        
    } catch (error) {
        console.error('页面初始化失败:', error);
    }
}

// 加载指定类别的数据
function loadCategoryData(category, reportDate = null, silent = false) {
    const actualReportDate = reportDate || currentReportDate;
    
    // 立即清理UI状态，防止显示之前的错误信息
    if (!silent) {
        const errorElement = document.getElementById(`${category}-error`);
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
    
    // 如果没有可用的报告期，先加载报告期
    if (!actualReportDate && availableReportDates.length === 0) {
        console.log('报告期未加载，先加载报告期数据');
        loadAvailableReportDates().then(success => {
            if (success) {
                loadCategoryData(category, reportDate, silent);
            } else {
                if (!silent) {
                    showError(category, '无法获取报告期信息');
                }
            }
        });
        return;
    }
    
    const cacheKey = `${category}_${actualReportDate || 'latest'}`;
    
    // 检查是否已有数据
    if (holdingsData[cacheKey]) {
        if (!silent) {
            displayHoldingsTable(category, holdingsData[cacheKey]);
        }
        updatePerformanceMetrics(true); // 缓存命中
        return;
    }
    
    // 防止重复请求
    if (loadingStates[category]) {
        return;
    }
    
    loadingStates[category] = true;
    const startTime = Date.now();
    
    // 非静默模式显示加载状态
    if (!silent) {
        showLoading(category);
        showPerformanceIndicator(`正在加载${getCategoryDisplayName(category)}数据...`);
        // 再次确保错误信息被隐藏
        const errorElement = document.getElementById(`${category}-error`);
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
    
    // 构建API URL
    let apiUrl = `/api/institutional_holdings/${category}`;
    if (actualReportDate && actualReportDate !== 'null' && actualReportDate !== null) {
        apiUrl += `?report_date=${actualReportDate}`;
    }
    
    // 发送API请求
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                holdingsData[cacheKey] = data.data;
                updatePerformanceMetrics(false); // 网络请求
                
                trackPerformance(category, startTime, true);
                console.log(`${getCategoryDisplayName(category)}数据加载完成 (${actualReportDate})`);
                
                // 如果不是静默加载，则显示数据
                if (!silent) {
                    displayHoldingsTable(category, data.data);
                    hideLoading(category);
                }
                
                // 隐藏性能指示器
                if (!silent) {
                    hidePerformanceIndicator();
                }
            } else {
                const errorMsg = data.message || '数据加载失败';
                console.error(`加载${getCategoryDisplayName(category)}数据失败:`, errorMsg);
                
                // 检查该类别是否已有成功加载的数据
                const hasSuccessfulData = Object.keys(holdingsData).some(key => 
                    key.startsWith(`${category}_`) && holdingsData[key] && holdingsData[key].length > 0
                );
                
                if (!silent && !hasSuccessfulData) {
                    showError(category, `加载${getCategoryDisplayName(category)}数据失败: ${errorMsg}`);
                    hidePerformanceIndicator();
                } else if (!silent) {
                    // 如果已有成功数据，只隐藏加载状态，不显示错误
                    hideLoading(category);
                    hidePerformanceIndicator();
                }
                trackPerformance(category, startTime, false);
            }
        })
        .catch(error => {
            console.error('请求出错:', error);
            
            // 检查该类别是否已有成功加载的数据
            const hasSuccessfulData = Object.keys(holdingsData).some(key => 
                key.startsWith(`${category}_`) && holdingsData[key] && holdingsData[key].length > 0
            );
            
            if (!silent && !hasSuccessfulData) {
                showError(category, '数据加载失败，请稍后重试');
                hidePerformanceIndicator();
            } else if (!silent) {
                // 如果已有成功数据，只隐藏加载状态，不显示错误
                hideLoading(category);
                hidePerformanceIndicator();
            }
            trackPerformance(category, startTime, false);
        })
        .finally(() => {
            loadingStates[category] = false;
        });
}

// 显示加载状态
function showLoading(category) {
    const loadingElement = document.getElementById(`${category}-loading`);
    const errorElement = document.getElementById(`${category}-error`);
    
    // 强制隐藏错误信息
    if (errorElement) {
        errorElement.style.display = 'none';
        errorElement.textContent = ''; // 清空错误文本
    }
    
    // 显示加载状态
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
}

// 隐藏加载状态
function hideLoading(category) {
    const loadingElement = document.getElementById(`${category}-loading`);
    const errorElement = document.getElementById(`${category}-error`);
    
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

// 显示错误信息
function showError(category, message) {
    const errorElement = document.getElementById(`${category}-error`);
    const loadingElement = document.getElementById(`${category}-loading`);
    
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// 显示持股数据表格
function displayHoldingsTable(category, data) {
    const tableBody = document.getElementById(`${category}-table-body`);
    const errorElement = document.getElementById(`${category}-error`);
    
    if (!tableBody) {
        console.error(`找不到表格元素: ${category}-table-body`);
        return;
    }
    
    // 隐藏错误信息
    if (errorElement) {
        errorElement.style.display = 'none';
    }
    
    // 清空现有数据
    tableBody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }
    
    // 填充数据
    data.forEach((stock, index) => {
        const row = document.createElement('tr');
        row.className = 'clickable-row';
        row.setAttribute('data-stock-code', stock.stock_code);
        row.setAttribute('data-stock-name', stock.stock_name);
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${stock.stock_code}</td>
            <td>${stock.stock_name}</td>
            <td>${stock.holding_ratio.toFixed(2)}%</td>
        `;
        
        // 添加点击事件
        row.addEventListener('click', function() {
            const stockCode = this.getAttribute('data-stock-code');
            const stockName = this.getAttribute('data-stock-name');
            showStockDetail(stockCode, stockName);
        });
        
        tableBody.appendChild(row);
    });
    
    console.log(`${getCategoryDisplayName(category)} 表格显示完成，共 ${data.length} 条记录`);
}

// 选择股票（直接调用个股查询功能）
function selectStock(category, stockCode, stockName, rowElement) {
    // 移除其他行的选中状态
    const allRows = document.querySelectorAll(`#tbody-${category} .stock-row`);
    allRows.forEach(row => row.classList.remove('selected-stock'));
    
    // 添加当前行的选中状态
    rowElement.classList.add('selected-stock');
    
    // 设置股票代码到输入框并直接调用查询功能
    const stockCodeInput = document.getElementById('stockCodeInput');
    if (stockCodeInput) {
        stockCodeInput.value = stockCode;
    }
    
    // 直接调用个股详情查询功能
    queryStockDetail();
}

// 加载股票持股变化图表
function loadStockHoldingsChart(category, stockCode, stockName) {
    // 隐藏占位符，显示加载状态
    const placeholder = document.getElementById(`chart-placeholder-${category}`);
    const canvas = document.getElementById(`chart-${category}`);
    
    if (placeholder) {
        placeholder.innerHTML = '加载图表数据中...';
        placeholder.style.display = 'flex';
    }
    if (canvas) canvas.style.display = 'none';
    
    // 发送API请求获取股票的持股变化数据
    fetch(`/api/institutional_holdings/${category}/${stockCode}/trend`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayHoldingsChart(category, stockCode, stockName, data.data);
            } else {
                console.error(`获取${stockCode}持股变化数据失败:`, data.message);
                if (placeholder) {
                    placeholder.innerHTML = '暂无图表数据';
                }
            }
        })
        .catch(error => {
            console.error('请求出错:', error);
            if (placeholder) {
                placeholder.innerHTML = '图表加载失败';
            }
        });
}

// 显示持股变化图表（优化版）
function displayHoldingsChart(category, stockCode, stockName, data) {
    const placeholder = document.getElementById(`chart-placeholder-${category}`);
    const canvas = document.getElementById(`chart-${category}`);
    
    if (!canvas || !data || data.length === 0) {
        if (placeholder) {
            placeholder.innerHTML = '暂无图表数据';
            placeholder.style.display = 'flex';
        }
        return;
    }
    
    // 隐藏占位符，显示图表
    if (placeholder) placeholder.style.display = 'none';
    canvas.style.display = 'block';
    
    // 销毁之前的图表
    if (charts[category]) {
        charts[category].destroy();
    }
    
    // 准备图表数据
    const labels = data.map(item => {
        const date = new Date(item.date);
        return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short' });
    });
    const values = data.map(item => item.holding_ratio);
    const changes = data.map(item => item.change_ratio || 0);
    
    // 计算颜色渐变
    const maxValue = Math.max(...values);
    const minValue = Math.min(...values);
    const colors = values.map(value => {
        const ratio = (value - minValue) / (maxValue - minValue);
        const red = Math.floor(255 * (1 - ratio));
        const green = Math.floor(255 * ratio);
        return `rgba(${red}, ${green}, 100, 0.6)`;
    });
    
    // 创建新图表
    const ctx = canvas.getContext('2d');
    charts[category] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${stockName} (${stockCode}) 持股比例`,
                data: values,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                pointBackgroundColor: colors,
                pointBorderColor: 'rgb(54, 162, 235)',
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: `${stockName} (${stockCode}) 持股变化趋势`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            const change = changes[index];
                            return change !== 0 ? `变化: ${change > 0 ? '+' : ''}${change.toFixed(2)}%` : '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: '持股比例 (%)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            }
        }
    });
}

// 工具函数：格式化数字
function formatNumber(num, decimals = 2) {
    return parseFloat(num).toFixed(decimals);
}

// 工具函数：格式化日期
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}