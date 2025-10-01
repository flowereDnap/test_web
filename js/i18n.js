// ==================== TRANSLATIONS ====================
const translations = {
    ru: {
        nav: {
            quests: 'Квесты',
            cash: 'Заработок',
            faq: 'FAQ'
        },
        cash: {
            balance: 'Ваш баланс',
            earn: 'Заработать',
            today: 'Сегодня',
            total: 'Всего заработано',
            earned: 'Заработано!'
        },
        quests: {
            title: '🎯 Квесты',
            description: 'Выполняй задания и получай награды',
            quest1: {
                title: 'Квест 1',
                text: 'Описание первого квеста'
            },
            quest2: {
                title: 'Квест 2',
                text: 'Описание второго квеста'
            },
            quest3: {
                title: 'Квест 3',
                text: 'Описание третьего квеста'
            }
        },
        faq: {
            title: '❓ FAQ',
            description: 'Часто задаваемые вопросы',
            question1: {
                title: 'Как это работает?',
                text: 'Здесь будет ответ на вопрос'
            },
            question2: {
                title: 'Как получить награду?',
                text: 'Здесь будет ответ на вопрос'
            },
            question3: {
                title: 'Техническая поддержка',
                text: 'Здесь будет контактная информация'
            }
        }
    },
    en: {
        nav: {
            quests: 'Quests',
            cash: 'Earn',
            faq: 'FAQ'
        },
        cash: {
            balance: 'Your Balance',
            earn: 'Earn',
            today: 'Today',
            total: 'Total Earned',
            earned: 'Earned!'
        },
        quests: {
            title: '🎯 Quests',
            description: 'Complete tasks and earn rewards',
            quest1: {
                title: 'Quest 1',
                text: 'Description of the first quest'
            },
            quest2: {
                title: 'Quest 2',
                text: 'Description of the second quest'
            },
            quest3: {
                title: 'Quest 3',
                text: 'Description of the third quest'
            }
        },
        faq: {
            title: '❓ FAQ',
            description: 'Frequently asked questions',
            question1: {
                title: 'How does it work?',
                text: 'Answer to the question will be here'
            },
            question2: {
                title: 'How to get a reward?',
                text: 'Answer to the question will be here'
            },
            question3: {
                title: 'Technical Support',
                text: 'Contact information will be here'
            }
        }
    }
};

// ==================== I18N HELPER ====================
function getTranslation(key, lang) {
    const keys = key.split('.');
    let value = translations[lang];
    
    for (const k of keys) {
        if (value && typeof value === 'object') {
            value = value[k];
        } else {
            return null;
        }
    }
    
    return value;
}

function applyTranslations(lang) {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translation = getTranslation(key, lang);
        if (translation) {
            el.textContent = translation;
        }
    });
}
