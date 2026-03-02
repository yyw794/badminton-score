/**
 * Firebase 配置
 * 
 * 使用方法：
 * 1. 访问 https://console.firebase.google.com/
 * 2. 创建新项目
 * 3. 添加 Web 应用
 * 4. 复制配置信息，替换下面的占位符
 */

const FIREBASE_CONFIG = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    databaseURL: "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
};

// 导出配置
export { FIREBASE_CONFIG };
