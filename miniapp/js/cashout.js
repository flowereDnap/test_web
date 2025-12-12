/**
 * js/cashout.js
 * Logic for the Cash Out Modal
 */

// ==================== CONFIGURATION ====================
const CASHOUT_OPTIONS = [
    {
        id: 'crypto_btc',
        name: 'Crypto Wallet (BTC)',
        icon: '₿',
        commission: 0.05, // 5%
        min_value: 10.00,
        min_time: '5',
        max_time: '24',
    },
    {
        id: 'visa_mc',
        name: 'Visa / Mastercard',
        icon: '💳',
        commission: 0.10, // 10%
        min_value: 20.00,
        min_time: '2',
        max_time: '5',
    },
    {
        id: 'paypal',
        name: 'PayPal',
        icon: '🅿️',
        commission: 0.08, // 8%
        min_value: 15.00,
        min_time: '1',
        max_time: '3',
    },
    {
        id: 'adv_cash',
        name: 'AdvCash',
        icon: '💵',
        commission: 0.03, // 3%
        min_value: 5.00,
        min_time: '12',
        max_time: '48',
    }
];

// ==================== DOM ELEMENTS ====================
const cashoutOverlay = document.getElementById('cashout-overlay');
const cashoutCloseBtn = document.getElementById('cashout-close');
const cashoutStepOptions = document.getElementById('cashout-step-options');
const cashoutBackBtn = document.getElementById('cashout-back-btn');
const cashoutStepInput = document.getElementById('cashout-step-input');
const cashoutOptionsList = cashoutStepOptions.querySelector('.cashout-options-list');
const cashoutInput = document.getElementById('cashout-amount-input');
const confirmCashoutBtn = document.getElementById('confirm-cashout-btn');
const detailMinValue = document.querySelector('.detail-min-value');
const detailCommission = document.querySelector('.detail-commission');
const detailTimeframe = document.querySelector('.detail-timeframe');
const cashOutBtn = document.getElementById('cash-out-btn'); // Button on the main CASH page

cashOutBtn.addEventListener('click', () => {
    showCashoutModal()
});

let selectedOption = null;

let userBalance = 100.00;

// ==================== RENDERING & UI FUNCTIONS ====================

/**
 * Renders the list of cashout options from the CASHOUT_OPTIONS array.
 */
function renderCashoutOptions() {
    // Очистка допустима, так как нет вложенного инлайнового JS
    cashoutOptionsList.innerHTML = ''; 

    CASHOUT_OPTIONS.forEach(option => {
        const button = document.createElement('button');
        button.className = 'cashout-option-btn';
        button.dataset.optionId = option.id;

        const iconSpan = document.createElement('span');
        iconSpan.className = 'option-icon';
        iconSpan.textContent = option.icon;

        const nameSpan = document.createElement('span');
        nameSpan.className = 'option-name';
        nameSpan.textContent = option.name;
        
        // Сборка
        button.appendChild(iconSpan);
        button.appendChild(nameSpan);

        cashoutOptionsList.appendChild(button);
    });
}
/**
 * Displays the cashout modal.
 */
function showCashoutModal() {
    // Reset to step 1 (options selection)
    cashoutStepOptions.classList.add('active');
    cashoutStepInput.classList.remove('active');
    cashoutOverlay.classList.add('active');
    cashoutBackBtn.style.display = 'none';
}

/**
 * Hides the cashout modal.
 */
function hideCashoutModal() {
    cashoutOverlay.classList.remove('active');
    selectedOption = null;
    cashoutInput.value = ''; // Clear input on close
}

/**
 * Switches the modal content to the input step and updates details.
 * @param {object} option - The selected cashout option object.
 */
function goToInputStep(option) {
    selectedOption = option;

    // Update caption details
    detailMinValue.textContent = `$${option.min_value.toFixed(2)}`;
    detailCommission.textContent = `${(option.commission * 100).toFixed(0)}%`;
    detailTimeframe.textContent = `${option.min_time} - ${option.max_time} ч.`;

    cashoutBackBtn.style.display = 'block';

    // Switch steps with a short delay for a smoother visual transition
    setTimeout(() => {
        cashoutStepOptions.classList.remove('active');
        cashoutStepInput.classList.add('active');
        cashoutInput.focus();
    }, 150);
}

function goToOptionsStep() {
    cashoutInput.value = ''; // Очищаем поле ввода при возврате
    selectedOption = null;
    cashoutBackBtn.style.display = 'none';
    
    cashoutStepInput.classList.remove('active');
    cashoutStepOptions.classList.add('active');
}

// ==================== EVENT HANDLERS ====================

/**
 * Handles clicks on the cashout option buttons.
 * @param {Event} e - The click event.
 */
function handleOptionSelect(e) {
    const btn = e.target.closest('.cashout-option-btn');
    if (!btn) return;

    const optionId = btn.dataset.optionId;
    const option = CASHOUT_OPTIONS.find(opt => opt.id === optionId);

    if (option) {
        goToInputStep(option);
    }
}

/**
 * Handles the final cashout confirmation button click.
 */
function handleConfirmCashout() {
    const amount = parseFloat(cashoutInput.value);
    
    if (!selectedOption) {
        // This shouldn't happen if the UI flow is correct
        console.error("No cashout option selected.");
        return;
    }

    if (isNaN(amount) || amount <= 0) {
        // TODO: Replace with a proper toast notification (assuming one exists or will be created)
        alert('Пожалуйста, введите корректную сумму.');
        return;
    }
    
    if (amount < selectedOption.min_value) {
         // TODO: Replace with a proper toast notification
        alert(`Минимальная сумма вывода для ${selectedOption.name} составляет $${selectedOption.min_value.toFixed(2)}.`);
        return;
    }

    // --- LOGIC TO BE IMPLEMENTED LATER ---
    console.log(`Запрос на вывод $${amount.toFixed(2)} через ${selectedOption.name}. Комиссия: ${selectedOption.commission * 100}%.`);
    // Placeholder for API call / submission logic
    
    // For now, just a success message and close
    alert('Заявка на вывод принята! (Логика будет реализована позже)');
    hideCashoutModal();
}

function handleInputValidation() {
    let value = cashoutInput.value;
    
    value = value.replace(/[^\d]/g, '');

    cashoutInput.value = value;
}

function handleConfirmCashout() {
    const amount = parseFloat(cashoutInput.value);
    
    // ... (Проверки: selectedOption, isNaN/amount <= 0, amount < min_value) ...

    // ИЗМЕНЕНИЕ 6: Проверка баланса (Пункт 5)
    if (amount > userBalance) {
        // Заглушка, позже нужно заменить на более красивое уведомление
        alert(`Недостаточно средств. Ваш баланс: $${userBalance.toFixed(2)}.`);
        return;
    }
    
    // --- API LOGIC ---
    console.log(`Запрос на вывод $${amount.toFixed(2)} через ${selectedOption.name}.`);
    // Здесь должен быть вызов Telegram.WebApp.sendData или AJAX-запрос
    
    // For now, just a success message and close
    alert('Заявка на вывод принята! (Логика будет реализована позже)');
    hideCashoutModal();
}


// ==================== INITIALIZATION ====================

// 1. Initial Render
renderCashoutOptions();

// 2. Event Listeners
cashOutBtn.addEventListener('click', showCashoutModal);
cashoutCloseBtn.addEventListener('click', hideCashoutModal);
cashoutOptionsList.addEventListener('click', handleOptionSelect);
confirmCashoutBtn.addEventListener('click', handleConfirmCashout);
cashoutBackBtn.addEventListener('click', goToOptionsStep);
cashoutInput.addEventListener('input', handleInputValidation);

// Optional: Allow pressing ESC to close the modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && cashoutOverlay.classList.contains('active')) {
        hideCashoutModal();
    }
});