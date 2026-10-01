import { Router } from 'express';
import {
  activateNavigation,
  getActiveNavigation,
  getNavigation,
} from '../controllers/navigationController';

export const navigationRoutes = Router();

navigationRoutes.get('/', getNavigation);
navigationRoutes.get('/active', getActiveNavigation);
navigationRoutes.post('/activate', activateNavigation);
