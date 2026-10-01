import { createApp } from './app';

const port = Number(process.env.PORT ?? 3001);

createApp().listen(port, () => {
  process.stdout.write(`acpos api listening on ${port}\n`);
});
