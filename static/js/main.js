/**
 * IAmSurfer - JavaScript principal
 */

// Espera o DOM carregar completamente
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa todos os tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializa todos os popovers do Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Adiciona a classe fade-in aos posts para animar sua entrada
    const posts = document.querySelectorAll('.card.shadow.mb-4');
    posts.forEach((post, index) => {
        setTimeout(() => {
            post.classList.add('fade-in');
        }, index * 100);
    });

    // Função para remover alertas automaticamente após 5 segundos
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Função para pré-visualização de imagens em formulários de upload
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    imageInputs.forEach(input => {
        if (!input.dataset.previewInitialized) {
            input.dataset.previewInitialized = "true";
            setupImagePreview(input);
        }
    });

    // Função para fazer as requisições de curtida via AJAX
    setupLikeButtons();

    // Função para confirmar exclusão
    setupDeleteConfirmations();
});

/**
 * Configura a pré-visualização de imagens para inputs de arquivo
 * @param {HTMLElement} input - O elemento input do tipo file
 */
function setupImagePreview(input) {
    const previewContainer = document.querySelector(`#${input.id}-preview`);
    if (!previewContainer) return;
    
    input.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                previewContainer.style.display = 'block';
                previewContainer.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded">`;
            };
            
            reader.readAsDataURL(file);
        } else {
            previewContainer.style.display = 'none';
            previewContainer.innerHTML = '';
        }
    });
}

/**
 * Configura os botões de curtir para usar AJAX
 */
function setupLikeButtons() {
    const likeButtons = document.querySelectorAll('.like-button');
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const postId = this.dataset.postId;
            const likeUrl = this.dataset.likeUrl;
            const likeCount = this.querySelector('.like-count');
            const likeIcon = this.querySelector('.like-icon');
            
            fetch(likeUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ post_id: postId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Atualiza o contador de curtidas
                    likeCount.textContent = data.likes_count;
                    
                    // Alterna a classe para mostrar que foi curtido
                    if (data.liked) {
                        button.classList.add('liked');
                        likeIcon.classList.remove('bi-heart');
                        likeIcon.classList.add('bi-heart-fill');
                    } else {
                        button.classList.remove('liked');
                        likeIcon.classList.remove('bi-heart-fill');
                        likeIcon.classList.add('bi-heart');
                    }
                }
            })
            .catch(error => console.error('Erro ao curtir post:', error));
        });
    });
}

/**
 * Configura confirmações para botões de exclusão
 */
function setupDeleteConfirmations() {
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Função para mostrar/esconder comentários
 * @param {number} postId - ID do post
 */
function toggleComments(postId) {
    const commentsSection = document.querySelector(`#comments-${postId}`);
    if (commentsSection) {
        commentsSection.classList.toggle('d-none');
    }
}

/**
 * Função para compartilhar um post
 * @param {number} postId - ID do post
 * @param {string} postUrl - URL do post
 */
function sharePost(postId, postUrl) {
    if (navigator.share) {
        navigator.share({
            title: 'Confira este post no IAmSurfer!',
            url: postUrl
        }).then(() => {
            console.log('Post compartilhado com sucesso');
        }).catch(error => {
            console.log('Erro ao compartilhar:', error);
        });
    } else {
        // Fallback para navegadores que não suportam a API Web Share
        const tempInput = document.createElement('input');
        document.body.appendChild(tempInput);
        tempInput.value = postUrl;
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        alert('Link do post copiado para a área de transferência!');
    }
} 