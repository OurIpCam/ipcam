const API_BASE = 'http://210.240.202.108:5000';
const token = localStorage.getItem('jwt');
const name = localStorage.getItem('name');


document.addEventListener('DOMContentLoaded', () => {
	const name = localStorage.getItem('name');
	
	setUserName(name);
	showUserProfileImage(token);
	setupLogout();
	setupProfileMenu();

});

/************** 將使用者名稱寫入畫面 *************/
function setUserName(name) {
	if (name) {
		document.querySelectorAll('.name').forEach(el => {
		el.innerText = name;
		});
	}
}

/************** 顯示使用者頭像（從 JWT 解碼） *************/
function showUserProfileImage(token) {
	if (!token) return;

	try {
		const base64Url = token.split('.')[1];
		const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
		const jsonPayload = decodeURIComponent(atob(base64).split('').map(c =>
		'%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
		).join(''));
		const payload = JSON.parse(jsonPayload);
	
		if (payload.picture_url) {
		document.querySelectorAll('.profile-pic-main, .profile-pic-menu').forEach(img => {
			img.src = payload.picture_url;
			img.onerror = () => {
			img.src = 'static/images/userHead/default/Crocodile.jpg';
			};
		});
		}
	} catch (e) {
		console.error('JWT 解碼錯誤:', e);
	}
}

/************** 登出功能（清除資料並導回首頁） *************/
function setupLogout() {
	const logoutBtn = document.querySelector('.logout');
	if (!logoutBtn) return;
	
	logoutBtn.addEventListener('click', () => {
		const token = localStorage.getItem('jwt');
		if (token) {
		fetch(`${API_BASE}/logout`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ token })
		});
		}
		localStorage.removeItem('jwt');
		localStorage.removeItem('name');
		window.location.href = '/index.html';
	});
}

/************** 頭像按鈕開關個人選單 *************/
function setupProfileMenu() {
	const profileBtn = document.getElementById('profile-btn');
	const profileMenu = document.getElementById('profile-menu');
	if (!profileBtn || !profileMenu) return;
	
	profileBtn.addEventListener('click', event => {
		event.stopPropagation();
		profileMenu.classList.toggle('show');
	});
	
	document.addEventListener('click', event => {
		if (!profileMenu.contains(event.target) && !profileBtn.contains(event.target)) {
		profileMenu.classList.remove('show');
		}
	});
}

document.querySelectorAll('#profile-menu .logout').forEach(item => {
    item.addEventListener('click', () => {
        profileMenu.classList.remove('show');
    });
});
