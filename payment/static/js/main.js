document.addEventListener('DOMContentLoaded', function() {
    class StoreFront {
        constructor() {
            this.apiBaseUrl = '/api/';  // Используем относительный URL
            this.cartCount = document.querySelector('.cart-count');
            this.productGrid = document.querySelector('.product-grid');
            this.initEventListeners();
            this.loadProducts();
            this.updateCartCount();
        }

        initEventListeners() {
            // Делегирование событий для динамически добавляемых элементов
            document.addEventListener('click', (e) => {
                if (e.target.classList.contains('add-to-cart')) {
                    this.addToCart(e);
                }
                if (e.target.classList.contains('remove-item')) {
                    this.removeItem(e);
                }
            });

            const checkoutBtn = document.getElementById('checkout-btn');
            if (checkoutBtn) {
                checkoutBtn.addEventListener('click', () => this.checkout());
            }
        }

        async loadProducts() {
            try {
                const response = await this._fetchApi('items/');
                if (response && this.productGrid) {
                    this.renderProducts(response);
                }
            } catch (error) {
                console.error('Error loading products:', error);
                this.showToast('Failed to load products', 'error');
            }
        }

        renderProducts(products) {
            this.productGrid.innerHTML = products.map(product => `
                <div class="product-card" data-product-id="${product.id}">
                    <h3>${product.name}</h3>
                    <p class="description">${product.description || ''}</p>
                    <div class="price">${product.price} ${product.currency}</div>
                    <button class="add-to-cart" data-product-id="${product.id}">
                        Add to Cart
                    </button>
                </div>
            `).join('');
        }

        async addToCart(event) {
            const button = event.target;
            const productId = button.dataset.productId;

            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = 'Adding...';

            try {
                // 1. Получаем текущий заказ
                const orderResponse = await this._fetchApi('orders/current/');

                if (orderResponse && orderResponse.id) {
                    // 2. Добавляем товар
                    await this._fetchApi(`orders/${orderResponse.id}/add_item/`, 'POST', {
                        item_id: productId,
                        quantity: 1
                    });

                    this.showToast('Item added to cart');
                    this.updateCartCount();
                }
            } catch (error) {
                console.error('Error adding to cart:', error);
                this.showToast('Error adding item', 'error');
            } finally {
                button.disabled = false;
                button.textContent = originalText;
            }
        }

        async removeItem(event) {
            const button = event.target;
            const cartItem = button.closest('.cart-item');
            const itemId = cartItem.dataset.itemId;

            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = 'Removing...';

            try {
                const orderResponse = await this._fetchApi('orders/current/');

                if (orderResponse && orderResponse.id) {
                    await this._fetchApi(
                        `orders/${orderResponse.id}/remove_item/${itemId}/`,
                        'DELETE'
                    );

                    cartItem.remove();
                    this.updateCartCount();
                    this.showToast('Item removed from cart');

                    if (!document.querySelector('.cart-item')) {
                        setTimeout(() => window.location.reload(), 1000);
                    }
                }
            } catch (error) {
                console.error('Error removing item:', error);
                this.showToast('Error removing item', 'error');
                button.disabled = false;
                button.textContent = originalText;
            }
        }

        async checkout() {
            const button = document.getElementById('checkout-btn');
            if (!button) return;

            button.disabled = true;
            const originalText = button.textContent;
            button.textContent = 'Processing...';

            try {
                const orderResponse = await this._fetchApi('orders/current/');

                if (orderResponse && orderResponse.id) {
                    const response = await this._fetchApi(
                        `orders/${orderResponse.id}/checkout/`,
                        'POST',
                        {
                            success_url: window.location.origin + '/order/success/',
                            cancel_url: window.location.origin + '/cart/'
                        }
                    );

                    if (response?.checkout_url) {
                        window.location.href = response.checkout_url;
                    }
                }
            } catch (error) {
                console.error('Checkout error:', error);
                this.showToast('Error during checkout', 'error');
            } finally {
                button.disabled = false;
                button.textContent = originalText;
            }
        }

        async updateCartCount() {
            try {
                const response = await this._fetchApi('orders/current/');
                if (response?.order_items) {
                    const count = response.order_items.reduce((sum, item) => sum + item.quantity, 0);
                    if (this.cartCount) {
                        this.cartCount.textContent = count;
                    }
                }
            } catch (error) {
                console.error('Error updating cart count:', error);
            }
        }

        async _fetchApi(endpoint, method = 'GET', data = null) {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'include'
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            try {
                const response = await fetch(`${this.apiBaseUrl}${endpoint}`, options);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || `Request failed: ${response.status}`);
                }

                return response.json();
            } catch (error) {
                console.error(`API Error (${endpoint}):`, error);
                throw error;
            }
        }

        _getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 300);
                }, 3000);
            }, 10);
        }
    }

    // Инициализация
    new StoreFront();
});