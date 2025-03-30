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
            
            // 创建图表
            new Chart(lhbChart, {
                type: 'bar',
                data: {
                    labels: data.codes,
                    datasets: [{
                        label: '龙虎榜出现次数',
                        data: data.counts,
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
                            text: '最近半年龙虎榜出现次数前十的股票',
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
                    }
                }
            });
        })
        .catch(error => {
            console.error('获取数据失败:', error);
            loading.innerHTML = '<p class="text-danger">数据加载失败，请刷新页面重试</p>';
        });
});