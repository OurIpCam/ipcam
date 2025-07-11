const API_BASE = 'http://210.240.202.108:5000';
const token = localStorage.getItem('jwt');

document.addEventListener('DOMContentLoaded', () => {
	const name = localStorage.getItem('name');
	
	setUserName(name);
	showUserProfileImage(token);
	setupLogout();
	setupProfileMenu();
	
	loadAllProjects(); // 顯示所有專案
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

/************** 左側選單 *************/
function toggleSidebar() {
	document.getElementById('sidebar').classList.toggle('active');
	document.querySelector('.sidebar-overlay').classList.toggle('active');
	document.querySelector('.hamburger-menu').classList.toggle('active');
	if (window.innerWidth > 768) {
		document.getElementById('content').classList.toggle('sidebar-open');
	}
}

function closeSidebar() {
	document.getElementById('sidebar').classList.remove('active');
	document.querySelector('.sidebar-overlay').classList.remove('active');
	document.querySelector('.hamburger-menu').classList.remove('active');
	document.getElementById('content').classList.remove('sidebar-open');
}


let projectDetials = [];			//所有專案
let currentPage = 1;
const PROJECTS_PER_PAGE = 50;
let totalPages = 1;

/***************************************** 讀取專案 ******************************************/
function loadAllProjects() {
	if (!token) {
		console.error('找不到 JWT，請重新登入');
		return;
	}
	
	fetch(`${API_BASE}/project`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ token })
	})
	.then(response => {
		if (!response.ok) throw new Error('伺服器錯誤');
		return response.json();
	})
    .then(data => {
		console.log('接收到 JSON：', data);

		/***********
		const 新陣列 = 原始陣列.map(每個元素 => {
		return 轉換後的值;
		});
		*************/
		
		projectDetials = data.map(p => ({
			project_id: p.project_id,
			project_name: p.project_name,
			camera_id: p.camera_id,
			camera_name: p.camera_name,
			device_id: p.device_id,
			device_name: p.device_name,
			create_date: (p.start_time || '').split('T')[0] || '-',
			status: p.status,
			contact_ids: p.contact_ids,
			contact_names: p.contact_names,
			model_ids: p.model_ids,
			model_names: p.model_names,
			event_ids: p.event_ids,
			event_names: p.event_names
		}));
	
		loadProjects();
    })
    .catch(err => {
		console.error('Fetch 過程出錯：', err);
    });
}

function calculatePagination(projects) {
	totalPages = Math.ceil(projects.length / PROJECTS_PER_PAGE);	//Math.ceil(...) 向上取整數
	if (currentPage > totalPages) currentPage = 1;
}

function getCurrentPageProjects(projects) {
	const start = (currentPage - 1) * PROJECTS_PER_PAGE;
	return projects.slice(start, start + PROJECTS_PER_PAGE);
}

function renderPagination() {
  const container = document.getElementById('pagination');
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }
  let html = '';
  html += `<button onclick="goToPage(${currentPage - 1})"${currentPage === 1 ? ' disabled' : ''}>‹ 上一頁</button>`;
  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, currentPage + 2);
  if (startPage > 1) {
    html += `<button onclick="goToPage(1)">1</button>`;
    if (startPage > 2) html += `<span>…</span>`;
  }
  for (let i = startPage; i <= endPage; i++) {
    html += `<button onclick="goToPage(${i})"${i === currentPage ? ' class="active"' : ''}>${i}</button>`;
  }
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) html += `<span>…</span>`;
    html += `<button onclick="goToPage(${totalPages})">${totalPages}</button>`;
  }
  html += `<button onclick="goToPage(${currentPage + 1})"${currentPage === totalPages ? ' disabled' : ''}>下一頁 ›</button>`;
  const startItem = (currentPage - 1) * PROJECTS_PER_PAGE + 1;
  const endItem = Math.min(currentPage * PROJECTS_PER_PAGE, filteredProjects.length);
  html += `<div class="page-info">顯示 ${startItem}-${endItem} 項，共 ${filteredProjects.length} 項</div>`;
  container.innerHTML = html;
}

function goToPage(page) {
  if (page < 1 || page > totalPages) return;
  currentPage = page;
  renderProjects(getCurrentPageProjects(filteredProjects));
  renderPagination();
  document.querySelector('.project-list').scrollIntoView({ behavior: 'smooth' });
}

function loadProjects() {
  calculatePagination(projectDetials);
  renderProjects(getCurrentPageProjects(filteredProjects));
  renderPagination();

}

function renderProjects(projects) {
  const list = document.getElementById('projectList');
  list.innerHTML = '';
  if (!projects.length) {
    list.innerHTML = `
      <div class="empty-state">
        <h3>尚無專案</h3>
        <p>點擊「新增專案」開始建立您的第一個監控專案</p>
      </div>`;
    return;
  }
  projects.forEach(p => {
    const card = document.createElement('div');
    card.className = 'project-card fade-in';
    card.dataset.id = p.project_id;

    const toggle = document.createElement('div');
    toggle.className = 'project-toggle';
    toggle.innerHTML = `
      <span class="toggle-label">${p.status === '1' ? '啟用' : '停用'}</span>
      <div class="toggle-switch ${p.status === '1' ? 'active' : ''}" onclick="toggleProjectStatus(${p.project_id}, event)">
        <div class="toggle-slider"></div>
      </div>`;
    card.appendChild(toggle);

card.innerHTML += `
  <div class="project-header"><h3>${p.project_name}</h3></div>
  <div class="project-info">
    <p><strong>攝影機:</strong> ${p.camera_name}</p>
    <p><strong>建立時間:</strong> ${p.create_date}</p>
	<p><strong>聯絡人:</strong> ${p.contact_names}</p>
	<p><strong>模型:</strong> ${p.model_names.join(', ')}</p>
	<p><strong>事件:</strong> ${p.event_names.join(', ')}</p>

  </div>
  <div class="project-tags">
    ${p.model_names.map(m => `<span class="tag">${m}</span>`).join('')}
  </div>`;


    card.addEventListener('click', (e) => {
		// 避免 toggle switch 觸發
		if (e.target.closest('.toggle-switch')) return;
		openEditModal(p);
    });
    list.appendChild(card);
  });
}

function toggleProjectStatus(projectId, event) {
  event.stopPropagation();
  const project = projectDetials.find(p => p.project_id === projectId);
  if (project) {
    project.status = project.status === '1' ? '0' : '1';
    
    console.log(`專案 "${project.project_name}" 已${project.status === '1' ? '啟用' : '停用'}`);
  }
}



/***************************************** 編輯專案 ******************************************/
function openEditModal(project) {
  document.getElementById('editModal').style.display = 'flex';
  document.getElementById('editProjectId').value = project.project_id;
  document.getElementById('editProjectName').value = project.project_name;
  document.getElementById('editCameraId').value = project.camera_id || '';
  document.getElementById('editStartTime').value = project.create_date ? new Date(project.create_date).toISOString().slice(0, 16) : '';
  document.getElementById('editStatus').value = project.status;
}

function closeEditModal() {
  document.getElementById('editModal').style.display = 'none';
}

function submitProjectEdit() {
  const token = localStorage.getItem('jwt');
  const project_id = document.getElementById('editProjectId').value;
  const project_name = document.getElementById('editProjectName').value;
  const camera_id = document.getElementById('editCameraId').value;
  const start_time = document.getElementById('editStartTime').value;
  const status = document.getElementById('editStatus').value;

  fetch(`${API_BASE}/project/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      project_id,
      project_name,
      camera_id,
      start_time,
      status
    })
  })
  .then(res => {
    if (!res.ok) throw new Error('更新失敗');
    alert('更新成功');
    closeEditModal();
    loadAllProjects(); // 重新載入資料
  })
  .catch(err => {
    alert('更新失敗：' + err.message);
    console.error(err);
  });
}