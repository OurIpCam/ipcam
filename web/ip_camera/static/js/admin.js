const API_BASE = 'http://210.240.202.108:5000';
const token = localStorage.getItem('jwt');
let currentUser = localStorage.getItem('currentUser');

document.addEventListener('DOMContentLoaded', () => {
    createBinaryElements();
	
	document.getElementById('quick-login').addEventListener('click', quickLoginAsAdmin);
	document.getElementById('login').addEventListener('click',loginAsAdmin);
	
	setupDragAndDrop();
	setupEditModelForm();
	setupEditDeviceForm();
	
    document.getElementById('btn-device-manage').addEventListener('click', deviceManage);
    document.getElementById('btn-model-manage').addEventListener('click', modelManage);	
	
});

function deviceManage() {
    document.getElementById('add-device-panel').style.display = 'block';
    document.getElementById('device-list-panel').style.display = 'block';
    document.getElementById('add-model-panel').style.display = 'none';
    document.getElementById('model-list-panel').style.display = 'none';
	
    document.getElementById('btn-device-manage').classList.add('active');
    document.getElementById('btn-model-manage').classList.remove('active');	
}

function modelManage() {
    document.getElementById('add-device-panel').style.display = 'none';
    document.getElementById('device-list-panel').style.display = 'none';
    document.getElementById('add-model-panel').style.display = 'block';
    document.getElementById('model-list-panel').style.display = 'block';
	
    document.getElementById('btn-model-manage').classList.add('active');
    document.getElementById('btn-device-manage').classList.remove('active');
}

//二進制背景動畫
function createBinaryElements() {
	const bg = document.getElementById('binary-background');
	const w = window.innerWidth, h = window.innerHeight;
	const chars = ['0','1'];
	function drop() {
		const el = document.createElement('div');
		el.className = 'binary';
		el.textContent = chars[Math.random()*2|0];
		const size = 12+Math.random()*8, speed = .5+Math.random()*1.5, opacity=.05+Math.random()*.15;
		let y = -30;
		el.style.cssText = `left:${Math.random()*w}px;top:${y}px;font-size:${size}px;opacity:${opacity}`;
		bg.appendChild(el);
		(function fall(){
		y+=speed;
		el.style.top = `${y}px`;
		if (y < h+50) requestAnimationFrame(fall);
		else el.remove();
		})();
	}
	for (let i=0;i<50;i++) setTimeout(drop, i*100);
	setInterval(drop, 3000);
}

//登入頁面消失，進入管理頁面
function showLogin() {
	document.getElementById('login-page').style.display = 'flex';
	document.getElementById('dashboard-page').style.display = 'none';
}

//顯示
function showDashboard() {
	document.getElementById('admin_id-display').textContent = currentUser||'管理員';
	document.getElementById('login-page').style.display = 'none';
	document.getElementById('dashboard-page').style.display = 'block';
	
	deviceManage();
}

/******************************* 快速登入 ********************************/
//fetch(`${API_BASE}/admin/fixed-token`,
function quickLoginAsAdmin() {
    const button = document.getElementById('quick-login');
	const admin_id = document.getElementById('admin_id').value.trim();
    const originalText = button.textContent;
	
	if(!admin_id){
		showMessage('login-message','請輸入管理員帳號!')
		return;
	}
	
    button.textContent = '登入中...';
    button.disabled = true;
    button.style.background = '#666';

    fetch(`${API_BASE}/admin/fixed-token`, {
        method: 'POST',
		headers: {'Content-Type':'application/json'},
		body: JSON.stringify({admin_id})
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(j => {
                throw new Error(j.error || '登入失敗');
            });
        }
        return res.json();
    })
    .then(data => {
        localStorage.setItem('jwt', data.token);
        localStorage.setItem('currentUser', data.admin_id);
        token = data.token;
        currentUser = data.admin_id;
		
        button.textContent = '登入成功';
		button.style.background = '#4CAF50';

        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
            button.style.background = '#000';
            showDashboard();
        }, 1000);
		
		loadModels();
    })
    .catch(err => {
        console.error(err);
        button.textContent = originalText;
        button.disabled = false;
        button.style.background = '#000';
        showMessage('login-message', err.message || '登入失敗');
		
		setTimeout(() => {
			document.getElementById('login-message').textContent = '';
		}, 3000);
    });
}

/***************************** 一般管理者登入 *****************************/
//fetch(`${API_BASE}/admin/login`,
function loginAsAdmin() {
    const admin_id = document.getElementById('admin_id').value.trim();
    const admin_password = document.getElementById('admin_password').value.trim();
    const button = document.getElementById('login');
    const originalText = button.textContent;

    if (!admin_id || !admin_password) {
        showMessage('login-message', '請輸入帳號和密碼');
        return;
    }

    button.textContent = '驗證中...';
    button.style.background = '#666';
    button.disabled = true;

    fetch(`${API_BASE}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_id, admin_password })
    })
    .then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            throw new Error('登入失敗，請確認帳號密碼');
        }
    })
    .then(data => {
        localStorage.setItem('jwt', data.token);
        localStorage.setItem('currentUser', data.admin_id);
        token = data.token;
        currentUser = admin_id;

        button.textContent = '登入成功';
        button.style.background = '#4CAF50';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '#000';
            button.disabled = false;
            document.getElementById('admin_id').value = '';
            document.getElementById('admin_password').value = '';
            showDashboard();
        }, 1000);
		
		loadModels();
    })
    .catch(error => {
        showMessage('login-message', error.message || '登入失敗');
        button.textContent = originalText;
        button.style.background = '#000';
        button.disabled = false;
    });
}

/******************************** 登出 ********************************/
function logout() {
	if (!confirm('確定要登出嗎？')) return;
	fetch(`${API_BASE}/admin/logout`, {
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body: JSON.stringify({token})
	})
	.then(res => {
		if (res.ok) {
		localStorage.clear();
		document.getElementById('admin_id-display').textContent = '';
		showLogin();
		} else return Promise.reject('登出失敗');
	})
	.catch(err => alert(`登出錯誤：${err}`));
}

//所有動作顯示訊息
function showMessage(containerId, msg, type) {
    const el = document.getElementById(containerId);
    el.textContent = msg;
    el.className = type; // 方便加 success/error 樣式
}

/********************************* 新增裝置 ********************************/
//fetch(`${API_BASE}/device/create`,
document.getElementById('add-device-form').addEventListener('submit', e => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('token', token || '');

    fetch(`${API_BASE}/device/create`, {
        method: 'POST',
        body: formData
    })
    .then(res => {
        if (res.status === 200) {
            showMessage('add-deviceMessage', '裝置新增成功！', 'success');
            setTimeout(() => {
                document.getElementById('add-deviceMessage').textContent = '';
            }, 3000);
            document.getElementById('add-device-form').reset();
            loadDevices();
        } else {
            return res.json().then(j => {
                showMessage('add-deviceMessage', j.error || '新增失敗', 'error');
            });
        }
    })
    .catch(() => showMessage('add-deviceMessage', '新增失敗', 'error'));
});

/********************************* 讀取裝置 ********************************/
//fetch(`${API_BASE}/device`,    還沒測!!!!!!!!!!!!!
function loadDevices() {
    fetch(`${API_BASE}/device`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token: token || '' })
    })
    .then(res => res.ok ? res.json() : Promise.reject(res))
    .then(data => {
        displayDevices(data.devices || []);
    })
    .catch(async err => {
        try {
            const j = await err.json();
            showMessage('devices-message', j.error || '裝置載入失敗', 'error');
        } catch {
            showMessage('devices-message', '裝置載入失敗', 'error');
        }
    });
}

function displayDevices(devices) {
    const tbody = document.getElementById('devices-tbody');
    tbody.innerHTML = '';

    if (!devices.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">暫無裝置資料</td></tr>';
        return;
    }

    devices.forEach((d, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${escapeHtml(d.device_id)}</td>
            <td>${escapeHtml(d.user_id)}</td>
            <td>${escapeHtml(d.Manufacture_date)}</td>
            <td>${escapeHtml(d.Model)}</td>
            <td class="action-buttons">
                <button class="btn btn-primary btn-small" onclick='editDevice(${JSON.stringify(d)})'>編輯</button>
                <button class="btn btn-danger btn-small" onclick="deleteDevice('${d.device_id}')">刪除</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/********************************* 編輯裝置 ******************************/
function editDevice(device) {
    document.getElementById('edit-device-id').value = device.device_id;
    document.getElementById('edit-user-id').value = device.user_id;

    document.getElementById('edit-device-modal').style.display = 'block';
}

//fetch(`${API_BASE}/device/update`,    還沒測!!!!!!!!!!!!!
function setupEditDeviceForm() {
    const form = document.getElementById('edit-device-form');

    form.addEventListener('submit', e => {
        e.preventDefault();

        const device_id = document.getElementById('edit-device-id').value.trim();
        const user_id = document.getElementById('edit-user-id').value.trim();

        const formData = new FormData();
        formData.append('token', token || '');
        formData.append('device_id', device_id);
        formData.append('user_id', user_id);

        fetch(`${API_BASE}/device/update`, {
            method: 'POST',
            body: formData
        })
        .then(async res => {
            if (res.ok) {
                showMessage('edit-device-message', '裝置更新成功！', 'success');
                setTimeout(() => {
                    closeEditDeviceModal();
                    loadDevices();
                }, 1500);
            } else {
                const data = await res.json();
                showMessage('edit-device-message', data.error || '更新失敗', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showMessage('edit-device-message', '更新時發生錯誤', 'error');
        });
    });
}

function closeEditDeviceModal() {
    document.getElementById('edit-device-modal').style.display = 'none';
    document.getElementById('edit-device-message').innerHTML = '';
}

window.addEventListener('click', e => {
    const modal = document.getElementById('edit-device-modal');
    if (e.target === modal) closeEditDeviceModal();
});

/********************************* 刪除裝置 ******************************/
//fetch(`${API_BASE}/device/delete`,    還沒測!!!!!!!!!!!!!
function deleteDevice(deviceId) {
    if (!confirm('確定要刪除這個裝置嗎？此操作無法復原。')) return;

    fetch(`${API_BASE}/device/delete`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            token: token || '',
            device_id: deviceId
        })
    })
    .then(res => res.ok ? res : Promise.reject(res))
    .then(() => {
        showMessage('devices-message', '裝置刪除成功！', 'success');
        setTimeout(() => {
            document.getElementById('devices-message').textContent = '';
        }, 3000);
        loadDevices();
    })
    .catch(res => res.json().then(j => {
        showMessage('devices-message', j.error || '刪除失敗', 'error');
    }));
}

/********************************* 新增模型 ********************************/
//上傳新增檔案
function handleFile(fileListBox, fileInput, file) {
    fileListBox.innerHTML = `<ul class="file-list"><li>${file.name}</li></ul>`;
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
}

//上傳新增檔案
function bindFileDrop(dropAreaId, fileInputId, fileListBoxId) {
    const dropArea = document.getElementById(dropAreaId);
    const fileInput = document.getElementById(fileInputId);
    const fileListBox = document.getElementById(fileListBoxId);

    dropArea.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, e => {
            e.preventDefault();
            dropArea.classList.add('highlight');
        });
    });
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, e => {
            e.preventDefault();
            dropArea.classList.remove('highlight');
        });
    });

    dropArea.addEventListener('drop', e => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            handleFile(fileListBox, fileInput, e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFile(fileListBox, fileInput, fileInput.files[0]);
        }
    });
}

// ---------- 新增模型 ----------
//fetch(`${API_BASE}/model/create`,
document.getElementById('add-model-form').addEventListener('submit', e => {
    e.preventDefault();

    const modelName = document.getElementById('model-name').value.trim();
    const modelVersion = document.getElementById('model-version').value.trim();
    const eventTypeRaw = document.getElementById('event-type').value.trim();
    const eventFile = document.getElementById('event-file-input-py').files[0];
    const modelFile = document.getElementById('event-file-input-pt').files[0];

    const eventList = eventTypeRaw
        .split(',')
        .map(e => e.trim())
        .filter(e => e.length > 0);

    if (!modelName || !modelVersion || eventList.length === 0 || !eventFile || !modelFile) {
        showMessage('add-message', '請完整填寫所有欄位與上傳檔案', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('token', token || '');
    formData.append('name', modelName);
    formData.append('version', modelVersion);
    formData.append('event', eventList.join(','));
    formData.append('py', eventFile);
    formData.append('pt', modelFile);

    fetch(`${API_BASE}/model/create`, {
        method: 'POST',
        body: formData
    })
    .then(res => {
        if (res.status === 200) {
            showMessage('add-message', '模型新增成功！', 'success');
			setTimeout(() => {
				document.getElementById('add-message').textContent = '';
			}, 3000);
			loadModels();
            document.getElementById('add-model-form').reset();
            document.getElementById('file-list-box-py').innerHTML = '';
            document.getElementById('file-list-box-pt').innerHTML = '';
            loadModels();
        } else {
            return res.json().then(j => {
                showMessage('add-message', j.error || '新增失敗', 'error');
            });
        }
    })
    .catch(() => showMessage('add-message', '新增失敗', 'error'));
});

/********************************* 讀取模型 ******************************/
function displayModels(models) {
    const tbody = document.getElementById('models-tbody');
    tbody.innerHTML = '';

    if (!models.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">暫無模型數據</td></tr>';
        return;
    }

    models.forEach((m, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${escapeHtml(m.model_name)}</td>
            <td>${escapeHtml(m.model_version)}</td>
            <td>${escapeHtml(m.event_type)}</td>
		<td class="action-buttons">
			<button class="btn btn-primary btn-small" onclick='editModel(${JSON.stringify(m)})'>編輯</button>
			<button class="btn btn-danger btn-small" onclick="deleteModel(${m.model_id})">刪除</button>
		</td>
        `;
        tbody.appendChild(row);
    });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
        "`": '&#096;'
    };
    return text.replace(/[&<>"'`]/g, m => map[m]);
}

// ---------- 讀取模型列表 ----------
//fetch(`${API_BASE}/model`,
function loadModels() {
    fetch(`${API_BASE}/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token || '' })
    })
    .then(res => res.ok ? res.json() : Promise.reject(res))
    .then(j => displayModels(j.models || []))
    .catch(async err => {
        try {
            const j = await err.json();
            showMessage('models-message', j.error || '載入失敗', 'error');
        } catch {
            showMessage('models-message', '載入失敗', 'error');
        }
    });
}

/********************************* 編輯模型 ******************************/
//上傳編輯檔案
function setupDragAndDrop() {
	setupUploadArea('event-drop-py', 'event-file-input-py', 'file-list-box-py');
	setupUploadArea('event-drop-pt', 'event-file-input-pt', 'file-list-box-pt');
	setupUploadArea('edit-event-drop-py', 'edit-event-file-input-py', 'edit-file-list-py');
	setupUploadArea('edit-event-drop-pt', 'edit-event-file-input-pt', 'edit-file-list-pt');
}

//上傳編輯檔案
function setupUploadArea(dropId, inputId, listBoxId) {
	const dropArea = document.getElementById(dropId);
	const fileInput = document.getElementById(inputId);
	const fileList = document.getElementById(listBoxId);

	dropArea.addEventListener('click', () => fileInput.click());

	['dragenter', 'dragover'].forEach(eventName => {
		dropArea.addEventListener(eventName, e => {
			e.preventDefault();
			dropArea.classList.add('highlight');
		});
	});

	['dragleave', 'drop'].forEach(eventName => {
		dropArea.addEventListener(eventName, e => {
			e.preventDefault();
			dropArea.classList.remove('highlight');
		});
	});

	dropArea.addEventListener('drop', e => {
		if (e.dataTransfer.files.length > 0) {
			fileInput.files = e.dataTransfer.files;
			displayFileName(fileList, fileInput.files[0]);
		}
	});

	fileInput.addEventListener('change', () => {
		if (fileInput.files.length > 0) {
			displayFileName(fileList, fileInput.files[0]);
		}
	});
}

function displayFileName(listElement, file) {
	listElement.innerHTML = `<li>${file.name}</li>`;
}

function editModel(model) {

    document.getElementById('edit-model-id').value = model.model_id || model.id;
    document.getElementById('edit-model-name').value = model.model_name || model.name || '';
    document.getElementById('edit-model-version').value = model.model_version || model.version || '';
   
    const rawEvent = model.event_type || model.event || '';
    const eventArray = Array.isArray(rawEvent)
        ? rawEvent
        : typeof rawEvent === 'string'
            ? rawEvent.split(',').map(e => e.trim())
            : [];
    document.getElementById('edit-event-type').value = eventArray.join(', ');

    // 顯示原本檔案名稱
    const fileListPy = document.getElementById('edit-file-list-py');
    const fileListPt = document.getElementById('edit-file-list-pt');
    const filename_py = document.getElementById('edit-event-file-input-py');
    const filename_pt = document.getElementById('edit-event-file-input-pt');

    // 清空檔案 input，讓使用者可選新檔案
    document.getElementById('edit-event-file-input-py').value = '';
    document.getElementById('edit-event-file-input-pt').value = '';

    // 顯示編輯模態框
    document.getElementById('edit-modal').style.display = 'block';
}

//fetch(`${API_BASE}/model/update`,
function setupEditModelForm() {
	const form = document.getElementById('edit-model-form');

	form.addEventListener('submit', e => {
		e.preventDefault();

		const modelId = document.getElementById('edit-model-id').value.trim();
		const modelName = document.getElementById('edit-model-name').value.trim();
		const modelVersion = document.getElementById('edit-model-version').value.trim();
		const eventTypesRaw = document.getElementById('edit-event-type').value.trim();
		const eventList = eventTypesRaw.split(',').map(e => e.trim()).filter(e => e);

		const eventFile = document.getElementById('edit-event-file-input-py').files[0];
		const modelFile = document.getElementById('edit-event-file-input-pt').files[0];

		const modelInfo = {
			name: modelName,
			version: modelVersion,
			event: eventList
		};

		const formData = new FormData();
		formData.append('token', token);
		formData.append('model_id', modelId);
		formData.append('model_event_info', JSON.stringify(modelInfo));
		if (eventFile) formData.append('py', eventFile, 'model.py');
		if (modelFile) formData.append('pt', modelFile, 'model.pt');

		fetch(`${API_BASE}/model/update`, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`
			},
			body: formData
		})
		.then(async res => {
			if (res.ok) {
				showMessage('edit-message', '模型更新成功！', 'success');
				setTimeout(() => {
					closeEditModal();
					if (typeof loadModels === 'function') loadModels();
				}, 1500);
			} else {
				const data = await res.json();
				showMessage('edit-message', data.error || '更新失敗', 'error');
			}
		})
		.catch(err => {
			console.error(err);
			showMessage('edit-message', '更新時發生錯誤', 'error');
		});
	});
}

function closeEditModal() {
	document.getElementById('edit-modal').style.display = 'none';
	document.getElementById('edit-message').innerHTML = '';
}

window.addEventListener('click', e => {
	const modal = document.getElementById('edit-modal');
	if (e.target === modal) closeEditModal();
});

/********************************* 刪除模型********************************/
//fetch(`${API_BASE}/model/delete`,
function deleteModel(id) {
	if (!confirm('確定要刪除這個模型嗎？此操作無法復原。')) return;

	fetch(`${API_BASE}/model/delete`, {
		method:'DELETE',
		headers:{'Content-Type':'application/json'},
		body: JSON.stringify({token, model_id:id})
	})
	.then(res=>res.ok?res:Promise.reject(res))
	.then(()=>{
		showMessage('models-message','模型刪除成功！','success');
		setTimeout(() => {
			document.getElementById('models-message').textContent = '';
		}, 3000);
		loadModels();
	})
	.catch(r=> r.json().then(j=>showMessage('models-message',j.error||'刪除失敗','error')));
}