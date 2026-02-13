document.addEventListener('DOMContentLoaded', () => {
  const usernameInput = document.getElementById('username');
  const feedback = document.getElementById('usernameFeedback');
  const form = document.querySelector('form[data-username-check-url]');

  if (usernameInput && !usernameInput.value) {
    usernameInput.focus();
  }

  if (!usernameInput || !feedback || !form) {
    return;
  }

  const checkUrl = form.dataset.usernameCheckUrl;
  const defaultMessage = feedback.dataset.defaultMessage || '아이디를 입력해주세요.';
  let debounceTimer = null;
  let activeController = null;
  let lastValue = '';

  const setFeedbackState = (state, message) => {
    feedback.dataset.state = state;
    feedback.textContent = message;
    feedback.classList.remove('text-gray-500', 'dark:text-gray-400', 'text-emerald-600', 'dark:text-emerald-400', 'text-red-600', 'dark:text-red-400');

    if (state === 'ok') {
      feedback.classList.add('text-emerald-600', 'dark:text-emerald-400');
    } else if (state === 'error') {
      feedback.classList.add('text-red-600', 'dark:text-red-400');
    } else {
      feedback.classList.add('text-gray-500', 'dark:text-gray-400');
    }
  };

  const checkUsername = async (rawValue) => {
    if (!checkUrl) {
      return;
    }

    const value = rawValue.trim();
    if (!value) {
      lastValue = '';
      setFeedbackState('idle', defaultMessage);
      return;
    }

    if (value === lastValue) {
      return;
    }

    lastValue = value;

    if (activeController) {
      activeController.abort();
    }
    activeController = new AbortController();

    setFeedbackState('checking', '아이디 확인 중...');

    try {
      const response = await fetch(`${checkUrl}?username=${encodeURIComponent(value)}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
        signal: activeController.signal,
      });

      const data = await response.json();
      if (data.available) {
        setFeedbackState('ok', data.message || '사용 가능한 아이디입니다.');
      } else {
        setFeedbackState('error', data.message || '이미 사용 중인 아이디입니다.');
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }
      setFeedbackState('error', '아이디 확인 중 오류가 발생했습니다.');
    }
  };

  const handleInput = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      checkUsername(usernameInput.value);
    }, 350);
  };

  usernameInput.addEventListener('input', handleInput);
  usernameInput.addEventListener('blur', () => checkUsername(usernameInput.value));

  const initialState = feedback.dataset.state || 'idle';
  if (initialState === 'error') {
    setFeedbackState('error', feedback.textContent || defaultMessage);
  } else {
    setFeedbackState('idle', feedback.textContent || defaultMessage);
  }
});
