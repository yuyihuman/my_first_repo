document.addEventListener('DOMContentLoaded', function() {
    // 获取页面元素
    const imageSelector = document.getElementById('imageSelector');
    const houseImage = document.getElementById('houseImage');
    const noImageSelected = document.getElementById('noImageSelected');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    // 初始化图表
    initPriceIndexAreaChart();
    
    // 获取图片列表
    fetch('/api/sh_house_price/images')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 填充下拉菜单
                data.images.forEach(image => {
                    const option = document.createElement('option');
                    option.value = image;
                    option.textContent = image;
                    imageSelector.appendChild(option);
                });
            } else {
                console.error('获取图片列表失败:', data.message);
                alert('获取图片列表失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('获取图片列表出错:', error);
            alert('获取图片列表出错: ' + error.message);
        });
    
    // 监听下拉菜单变化
    imageSelector.addEventListener('change', function() {
        const selectedImage = this.value;
        
        if (selectedImage) {
            // 显示加载动画
            loadingSpinner.style.display = 'block';
            houseImage.style.display = 'none';
            noImageSelected.style.display = 'none';
            
            // 设置图片路径
            houseImage.src = `/sh_house_price/images/${selectedImage}`;
            
            // 图片加载完成后显示
            houseImage.onload = function() {
                loadingSpinner.style.display = 'none';
                houseImage.style.display = 'block';
            };
            
            // 图片加载失败处理
            houseImage.onerror = function() {
                loadingSpinner.style.display = 'none';
                noImageSelected.textContent = '图片加载失败，请重试或选择其他图片';
                noImageSelected.style.display = 'block';
            };
        } else {
            // 未选择图片时显示提示
            houseImage.style.display = 'none';
            noImageSelected.textContent = '请从上方下拉菜单选择一个图表查看';
            noImageSelected.style.display = 'block';
        }
    });
});

// 初始化价格指数与面积对比图表
function initPriceIndexAreaChart() {
    const chartLoadingSpinner = document.getElementById('chartLoadingSpinner');
    chartLoadingSpinner.style.display = 'block';
    
    // 获取上海房价数据
    fetch('/api/sh_house_price/data')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 构建包含最新数据日期的标题
                let title = data.description || '上海房价指数与成交面积对比';
                if (data.latest_data_date) {
                    title += ` (数据更新至: ${data.latest_data_date})`;
                }
                
                createPriceIndexAreaChart(data.data, title);
            } else {
                console.error('获取房价数据失败:', data.message);
                alert('获取房价数据失败: ' + data.message);
            }
        })
        .catch(error => {
            console.error('获取房价数据出错:', error);
            alert('获取房价数据出错: ' + error.message);
        })
        .finally(() => {
            chartLoadingSpinner.style.display = 'none';
        });
}

// 创建价格指数与面积对比图表
function createPriceIndexAreaChart(data, description) {
    const ctx = document.getElementById('priceIndexAreaChart').getContext('2d');
    
    // 准备数据
    const labels = data.map(item => item.date);
    const priceIndexData = data.map(item => item.price_index);
    const totalAreaData = data.map(item => item.total_area);
    
    // 为不同年份生成不同颜色
    const yearColors = {
        2016: 'rgba(255, 99, 132, 0.6)',   // 红色
        2017: 'rgba(54, 162, 235, 0.6)',   // 蓝色
        2018: 'rgba(255, 205, 86, 0.6)',   // 黄色
        2019: 'rgba(75, 192, 192, 0.6)',   // 青色
        2020: 'rgba(153, 102, 255, 0.6)',  // 紫色
        2021: 'rgba(255, 159, 64, 0.6)',   // 橙色
        2022: 'rgba(199, 199, 199, 0.6)',  // 灰色
        2023: 'rgba(83, 102, 255, 0.6)',   // 靛蓝色
        2024: 'rgba(255, 99, 255, 0.6)',   // 品红色
        2025: 'rgba(99, 255, 132, 0.6)'    // 绿色
    };
    
    // 为每个数据点分配颜色，区分实际数据和估算数据
    const backgroundColors = data.map(item => {
        let baseColor = yearColors[item.year] || 'rgba(128, 128, 128, 0.6)';
        // 如果是估算数据，使用更透明的颜色
        if (item.is_estimated) {
            baseColor = baseColor.replace('0.6', '0.3');
        }
        return baseColor;
    });
    
    const borderColors = data.map(item => {
        let baseColor = yearColors[item.year] || 'rgba(128, 128, 128, 0.6)';
        let borderColor = baseColor.replace('0.6', '1');
        // 如果是估算数据，使用虚线边框效果（通过颜色变化体现）
        if (item.is_estimated) {
            borderColor = borderColor.replace('1)', '0.7)');
        }
        return borderColor;
    });
    
    // 为估算数据设置边框样式
    const borderDash = data.map(item => {
        return item.is_estimated ? [5, 5] : [];
    });
    
    // 创建图表
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '房价指数',
                    data: priceIndexData,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(255, 99, 132, 1)',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: 'rgba(231, 76, 60, 1)',
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3,
                    tension: 0.1,
                    yAxisID: 'y'
                },
                {
                    label: '成交面积 (平方米)',
                    data: totalAreaData.map((value, index) => {
                        if (data[index].is_estimated) {
                            // 对于估算数据，显示实际部分
                            return data[index].actual_value || 0;
                        } else {
                            return value;
                        }
                    }),
                    type: 'bar',
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 1,
                    hoverBackgroundColor: backgroundColors.map(color => color.replace('0.6)', '0.8)')),
                    hoverBorderColor: borderColors,
                    hoverBorderWidth: 2,
                    yAxisID: 'y1'
                },
                {
                    label: '成交面积 (估算)',
                    data: totalAreaData.map((value, index) => {
                        if (data[index].is_estimated) {
                            // 对于估算数据，显示估算部分（总值减去实际值）
                            return value - (data[index].actual_value || 0);
                        } else {
                            return null;
                        }
                    }),
                    type: 'bar',
                    backgroundColor: 'rgba(255, 87, 51, 0.8)', // 橙红色，对比度强
                    borderColor: 'rgba(255, 87, 51, 1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    hoverBackgroundColor: 'rgba(255, 87, 51, 0.9)',
                    hoverBorderColor: 'rgba(255, 87, 51, 1)',
                    hoverBorderWidth: 3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            hover: {
                mode: 'index',
                intersect: false,
                animationDuration: 200
            },
            plugins: {
                title: {
                    display: true,
                    text: description || '上海房价指数与成交面积对比',
                    font: {
                        size: 16
                    }
                },
                legend: {
                     display: true,
                     position: 'top',
                     labels: {
                         generateLabels: function(chart) {
                             const original = Chart.defaults.plugins.legend.labels.generateLabels;
                             const labels = original.call(this, chart);
                             
                             // 添加年份颜色图例
                             const yearColors = {
                                 2016: 'rgba(255, 99, 132, 0.6)',
                                 2017: 'rgba(54, 162, 235, 0.6)',
                                 2018: 'rgba(255, 205, 86, 0.6)',
                                 2019: 'rgba(75, 192, 192, 0.6)',
                                 2020: 'rgba(153, 102, 255, 0.6)',
                                 2021: 'rgba(255, 159, 64, 0.6)',
                                 2022: 'rgba(199, 199, 199, 0.6)',
                                 2023: 'rgba(83, 102, 255, 0.6)',
                                 2024: 'rgba(255, 99, 255, 0.6)',
                                 2025: 'rgba(99, 255, 132, 0.6)'
                             };
                             
                             // 获取数据中存在的年份
                             const existingYears = [...new Set(chart.data.labels.map((dateStr, index) => {
                                 if (dateStr && typeof dateStr === 'string') {
                                     return parseInt(dateStr.split('-')[0]);
                                 }
                                 return null;
                             }).filter(year => year !== null))].sort();
                             
                             // 为每个存在的年份添加图例项
                             existingYears.forEach(year => {
                                 if (yearColors[year]) {
                                     labels.push({
                                         text: year + '年',
                                         fillStyle: yearColors[year],
                                         strokeStyle: yearColors[year].replace('0.6', '1'),
                                         lineWidth: 1,
                                         hidden: false,
                                         index: labels.length
                                     });
                                 }
                             });
                             
                             return labels;
                         }
                     }
                 },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            return '日期: ' + context[0].label;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                if (context.dataset.label.includes('房价指数')) {
                                    label += context.parsed.y.toFixed(2);
                                } else {
                                    label += context.parsed.y.toLocaleString() + ' 平方米';
                                }
                            }
                            return label;
                        },
                        afterBody: function(context) {
                            // 显示总成交面积（实际+估算）
                            const dataIndex = context[0].dataIndex;
                            const chartData = context[0].chart.data;
                            let actualArea = 0;
                            let estimatedArea = 0;
                            
                            chartData.datasets.forEach(dataset => {
                                if (dataset.label.includes('成交面积')) {
                                    const value = dataset.data[dataIndex];
                                    if (value !== null && value !== undefined) {
                                        if (dataset.label.includes('估算')) {
                                            estimatedArea = value;
                                        } else {
                                            actualArea = value;
                                        }
                                    }
                                }
                            });
                            
                            if (estimatedArea > 0) {
                                const total = actualArea + estimatedArea;
                                return ['', `总成交面积: ${total.toLocaleString()} 平方米`, `(实际: ${actualArea.toLocaleString()}, 估算: ${estimatedArea.toLocaleString()})`];
                            }
                            return [];
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    stacked: true,
                    title: {
                        display: true,
                        text: '时间'
                    },
                    ticks: {
                        autoSkip: false,
                        callback: function(value) {
                            // 根据日期字符串(YYYY-MM)每三个月显示一次标签
                            const label = this.getLabelForValue(value);
                            if (typeof label === 'string' && label.includes('-')) {
                                const parts = label.split('-');
                                const month = parseInt(parts[1], 10);
                                // 显示 1、4、7、10 月（每三个月）
                                if (!isNaN(month) && ((month - 1) % 3 === 0)) {
                                    return label;
                                }
                            }
                            return '';
                        },
                        maxRotation: 0,
                        minRotation: 0
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '房价指数',
                        color: 'rgba(255, 99, 132, 1)'
                    },
                    ticks: {
                        color: 'rgba(255, 99, 132, 1)'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    stacked: true,
                    title: {
                        display: true,
                        text: '成交面积 (平方米)',
                        color: 'rgba(54, 162, 235, 1)'
                    },
                    ticks: {
                        color: 'rgba(54, 162, 235, 1)',
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    beginAtZero: true
                }
            }
         }
     });
     
     // 保存原始数据到图表配置中，供工具提示使用
     chart.config._config.rawData = data;
}