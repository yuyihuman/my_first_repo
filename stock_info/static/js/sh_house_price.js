document.addEventListener('DOMContentLoaded', function() {
    // 获取页面元素
    const imageSelector = document.getElementById('imageSelector');
    const houseImage = document.getElementById('houseImage');
    const noImageSelected = document.getElementById('noImageSelected');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
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