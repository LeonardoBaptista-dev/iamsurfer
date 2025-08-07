/**
 * IAmSurfer - Sistema de Imagens Responsivas
 * Sistema avançado de visualização de imagens similar ao Instagram
 * Inclui: lazy loading, modal, progressive loading, quality indicators
 */

class ImageViewer {
    constructor() {
        this.modal = null;
        this.currentImage = null;
        this.gallery = [];
        this.currentIndex = 0;
        this.lazyObserver = null;
        this.init();
    }

    init() {
        this.createModal();
        this.bindEvents();
        this.setupLazyLoading();
        this.setupProgressiveLoading();
        this.detectConnectionSpeed();
    }

    createModal() {
        // Cria modal para visualização em tela cheia com navegação
        this.modal = document.createElement('div');
        this.modal.className = 'image-modal fade';
        this.modal.innerHTML = `
            <div class="modal-content">
                <span class="close btn-close">&times;</span>
                <div class="modal-body">
                    <img src="" alt="Imagem em tela cheia" class="modal-image">
                    <div class="image-navigation d-none">
                        <button class="nav-btn prev-btn">&lt;</button>
                        <span class="image-counter">1 / 1</span>
                        <button class="nav-btn next-btn">&gt;</button>
                    </div>
                    <div class="image-info">
                        <div class="image-details"></div>
                        <div class="image-quality-badge"></div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(this.modal);

        // Eventos do modal
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal || e.target.classList.contains('close')) {
                this.closeModal();
            }
        });

        // Navegação por teclado
        document.addEventListener('keydown', (e) => {
            if (this.modal.style.display === 'block') {
                switch(e.key) {
                    case 'Escape':
                        this.closeModal();
                        break;
                    case 'ArrowLeft':
                        this.showPrevious();
                        break;
                    case 'ArrowRight':
                        this.showNext();
                        break;
                }
            }
        });

        // Botões de navegação
        this.modal.querySelector('.prev-btn').addEventListener('click', () => this.showPrevious());
        this.modal.querySelector('.next-btn').addEventListener('click', () => this.showNext());
    }

    bindEvents() {
        // Adiciona evento de clique para todas as imagens de posts
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('post-image') || e.target.closest('.image-gallery')) {
                this.openModal(e.target);
            }
        });

        // Preview ao passar o mouse (desktop)
        if (!this.isMobile()) {
            document.addEventListener('mouseover', (e) => {
                if (e.target.classList.contains('thumbnail')) {
                    this.showPreview(e.target);
                }
            });

            document.addEventListener('mouseout', (e) => {
                if (e.target.classList.contains('thumbnail')) {
                    this.hidePreview();
                }
            });
        }
    }

    openModal(imgElement) {
        const modalImg = this.modal.querySelector('img');
        
        // Tenta pegar a versão em alta resolução
        let highResUrl = imgElement.src;
        
        // Se a imagem tem data attributes com URLs diferentes
        if (imgElement.dataset.largeUrl) {
            highResUrl = imgElement.dataset.largeUrl;
        }
        // Se for um srcset, pega a maior resolução
        else if (imgElement.srcset) {
            const srcsetArray = imgElement.srcset.split(',');
            const lastSrc = srcsetArray[srcsetArray.length - 1].trim();
            highResUrl = lastSrc.split(' ')[0];
        }

        modalImg.src = highResUrl;
        modalImg.alt = imgElement.alt || 'Imagem ampliada';
        
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden';

        // Adiciona indicador de carregamento
        modalImg.style.opacity = '0.5';
        modalImg.onload = () => {
            modalImg.style.opacity = '1';
        };
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        
        // Limpa a imagem para economizar memória
        const modalImg = this.modal.querySelector('img');
        modalImg.src = '';
    }

    setupLazyLoading() {
        // Intersection Observer para lazy loading melhorado
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        
                        // Carrega imagem de alta qualidade quando estiver próxima
                        if (img.dataset.highQualitySrc && !img.dataset.highQualityLoaded) {
                            const highQualityImg = new Image();
                            highQualityImg.onload = () => {
                                img.src = img.dataset.highQualitySrc;
                                img.dataset.highQualityLoaded = 'true';
                                img.classList.add('high-quality-loaded');
                            };
                            highQualityImg.src = img.dataset.highQualitySrc;
                        }

                        observer.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.1
            });

            // Observa todas as imagens de posts
            document.querySelectorAll('.post-image[data-high-quality-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    showPreview(thumbnailElement) {
        // Implementar preview hover se necessário
        // Por enquanto, apenas adiciona efeito visual
        thumbnailElement.style.transform = 'scale(1.1)';
        thumbnailElement.style.zIndex = '10';
    }

    hidePreview() {
        // Remove preview hover
        document.querySelectorAll('.thumbnail').forEach(thumb => {
            thumb.style.transform = '';
            thumb.style.zIndex = '';
        });
    }

    isMobile() {
        return window.innerWidth <= 768;
    }

    // Método para adicionar indicadores de qualidade
    addQualityIndicators() {
        document.querySelectorAll('.post-image').forEach(img => {
            if (img.naturalWidth && !img.querySelector('.image-quality-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'image-quality-indicator';
                
                if (img.naturalWidth >= 1080) {
                    indicator.textContent = 'HD';
                    indicator.classList.add('quality-hd');
                } else if (img.naturalWidth >= 640) {
                    indicator.textContent = 'SD';
                    indicator.classList.add('quality-standard');
                } else {
                    indicator.textContent = 'LQ';
                    indicator.classList.add('quality-low');
                }

                // Adiciona o indicador ao container pai
                const container = img.parentElement;
                if (container && getComputedStyle(container).position === 'static') {
                    container.style.position = 'relative';
                }
                container.appendChild(indicator);
            }
        });
    }
}

// Classe para otimização de performance
class ImageOptimizer {
    static preloadNextImages() {
        // Pré-carrega imagens que provavelmente serão visualizadas
        const postImages = document.querySelectorAll('.post-image');
        const currentScrollPos = window.scrollY;
        const windowHeight = window.innerHeight;

        postImages.forEach((img, index) => {
            const imgTop = img.offsetTop;
            const distanceFromView = imgTop - (currentScrollPos + windowHeight);
            
            // Pré-carrega imagens que estão até 2 telas de distância
            if (distanceFromView < windowHeight * 2 && distanceFromView > 0) {
                if (img.dataset.preloadSrc && !img.dataset.preloaded) {
                    const preloadImg = new Image();
                    preloadImg.src = img.dataset.preloadSrc;
                    img.dataset.preloaded = 'true';
                }
            }
        });
    }

    static optimizeForConnection() {
        // Detecta velocidade de conexão e ajusta qualidade
        if ('connection' in navigator) {
            const connection = navigator.connection;
            const isSlowConnection = connection.effectiveType === '2g' || 
                                   connection.effectiveType === 'slow-2g';
            
            if (isSlowConnection) {
                // Força uso de imagens de menor qualidade
                document.documentElement.classList.add('slow-connection');
            }
        }
    }

    static enableProgressiveLoading() {
        // Carrega versão de baixa qualidade primeiro, depois alta qualidade
        document.querySelectorAll('.post-image[data-low-quality-src]').forEach(img => {
            if (img.dataset.lowQualitySrc && !img.dataset.progressiveLoaded) {
                // Carrega versão baixa qualidade primeiro
                const lowQualityImg = new Image();
                lowQualityImg.onload = () => {
                    img.src = img.dataset.lowQualitySrc;
                    img.style.filter = 'blur(2px)';
                    
                    // Depois carrega alta qualidade
                    if (img.dataset.highQualitySrc) {
                        const highQualityImg = new Image();
                        highQualityImg.onload = () => {
                            img.src = img.dataset.highQualitySrc;
                            img.style.filter = '';
                            img.dataset.progressiveLoaded = 'true';
                        };
                        highQualityImg.src = img.dataset.highQualitySrc;
                    }
                };
                lowQualityImg.src = img.dataset.lowQualitySrc;
            }
        });
    }
}

// Inicializa quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    const imageViewer = new ImageViewer();
    
    // Otimizações de performance
    ImageOptimizer.optimizeForConnection();
    ImageOptimizer.enableProgressiveLoading();
    
    // Pré-carregamento com throttle
    let preloadTimer;
    window.addEventListener('scroll', () => {
        clearTimeout(preloadTimer);
        preloadTimer = setTimeout(() => {
            ImageOptimizer.preloadNextImages();
        }, 100);
    });
    
    // Adiciona indicadores de qualidade após um delay
    setTimeout(() => {
        imageViewer.addQualityIndicators();
    }, 1000);
});

// Exporta para uso global se necessário
window.IAmSurferImageSystem = {
    ImageViewer,
    ImageOptimizer
};
