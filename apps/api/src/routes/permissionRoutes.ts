import { Router, type Request, type Response, type NextFunction } from 'express';
import { getAssignment } from '../repositories/permissionRepository';

export const permissionRoutes = Router();

permissionRoutes.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const accountUid = req.principal?.accountUid ?? req.header('x-account-uid') ?? '';
    const assignment = await getAssignment(accountUid);
    if (!assignment) {
      res.status(404).json({
        error: { code: 'PERMISSION_ASSIGNMENT_UNAVAILABLE', message: `No assignment for ${accountUid}` },
      });
      return;
    }
    res.status(200).json(assignment);
  } catch (error) {
    next(error);
  }
});
