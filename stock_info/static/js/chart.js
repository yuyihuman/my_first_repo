// 龙虎榜图表相关JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在龙虎榜页面
    const lhbChart = document.getElementById('lhbChart');
    if (!lhbChart) return;
    
    // 显示加载状态
    const loading = document.getElementById('loading');
    
    // 获取龙虎榜数据
    fetch('/api/lhb_data')
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            loading.style.display = 'none';

            // 只取前30个
            const codes = data.codes.slice(0, 30);
            const counts = data.counts.slice(0, 30);

            // 提取股票代码数组
            const stockCodes = codes.map(item => {
                // 从"股票名称(股票代码)"格式中提取股票代码
                const match = item.match(/\((\d+)\)/);
                return match ? match[1] : null;
            });

            // 创建图表
            const chart = new Chart(lhbChart, {
                type: 'bar',
                data: {
                    labels: codes,
                    datasets: [{
                        label: '龙虎榜出现次数',
                        data: counts,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '出现次数'
                            },
                            ticks: {
                                precision: 0
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '股票名称(代码)'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '最近一年龙虎榜出现次数前三十的股票',
                            font: {
                                size: 16
                            }
                        },
                        tooltip: {
                            callbacks: {
                                title: function(tooltipItems) {
                                    return tooltipItems[0].label;
                                },
                                label: function(context) {
                                    return `出现次数: ${context.raw}`;
                                }
                            }
                        }
                    },
                    // 添加点击事件处理
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const stockCode = stockCodes[index];
                            if (stockCode) {
                                // 跳转到个股信息页面并传递股票代码
                                window.location.href = `/stock_info?code=${stockCode}`;
                            }
                        }
                    },
                    // 添加鼠标样式，提示可点击
                    onHover: (event, elements) => {
                        const canvas = event.chart.canvas;
                        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                    }
                }
            });
        })
        .catch(error => {
            console.error('获取数据失败:', error);
            loading.innerHTML = '<p class="text-danger">数据加载失败，请刷新页面重试</p>';
        });
});