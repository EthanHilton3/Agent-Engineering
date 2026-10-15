import './style.css';
import { startApp } from './ui/app';

const root = document.querySelector<HTMLElement>('#app');
if (!root) throw new Error('Missing #app element');
startApp(root);
