import type { VisualStyleId, VisualStyleOption } from '../types/workflow';

export const PRIMARY_NAV_LINKS = [] as const;

export const STORY_NAV_LINKS = [] as const;

export const PROCESSING_NAV_LINKS = [] as const;

export const STORY_PLACEHOLDER =
  'Start typing your story script here...\n\nExample: In a world where AI creates art, one artist discovers the soul in the machine...';

export const STYLE_OPTIONS: VisualStyleOption[] = [
  {
    id: 'webtoon_cel',
    title: 'Webtoon Cel',
    description:
      '2D cel shading, crisp line art, korean webtoon style with flat colors and high contrast.',
    imageUrl:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuDYku5tNLyhFM1AUZ1HuX-nwvar-dtshNBkO5BlVynb7cxkNZNfm-1YrIvFSK1CRYVZ8QJ_mwalLh1c4xAJhuS8QgKWe1F3vMZjVACnNQvyyiMuQOLBu-n_WFz5O4R8fIFYrVvdgqVQZgBvKnenK5NtAdeMCwjMrlNk9C_GSYQxbQ2Slv_wXmx9Xcy1Ce0HBFtZMlL3CXC7pwlW46uYZAZzvVxllreLpCBQm9Y3VOVZs4EdTMqUXZGEX6CFcpvS3jFUi2w7aGfeDwg',
  },
  {
    id: 'cinematic_realism',
    title: 'Cinematic Realism',
    description:
      'Semi-realistic with cinematic lighting, dramatic shadows, and photorealistic textures.',
    imageUrl:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAYmW5B1jy_CMkMPeVMp6uhqLzsGYsg7gRy4jbIqZHoUdWANNjFQOHE9w1Ww2bJ5IkgJjOmz8_fKxQRhIfXMlk3S0pJNTeVp714E5XBHfVi_JE_fWZTIcvKeGWxgVja875stfQLzxqTt4UBvSn6sVTX5WBsxsDRh05sAToHfbTBEIkUY-P8hSoIpE3BXiMS0XuLsVm_2xZym5GPvv60BcAOoEiJb1hFfkyJUh5ywGDymniMvgZLsgu7YeLcOVHC6mjsLXuoAMSide4',
  },
  {
    id: 'watercolor_dream',
    title: 'Watercolor Dream',
    description:
      'Soft pastel watercolors, fluid brush strokes, dreamy ethereal atmosphere with paper texture.',
    imageUrl:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuB4OG6rgE4TCU4gbdhAFbhrgubf8C4KR5Ad6VXT7WdXrHZpeQycooh9nEippWRdo7k9EZrj5Rslj75XS6Qo3AFOBlH0OeSH_5VsuYhQAUlCnaxCIKGBDQD7go9bb9kkGb08wIJXdUe8WlAR_g_9EdVAmu8N8RE5ROvn6nNtZ2Qz4jqY-bzNb5bdOnJHlslm5G6FmV7QaQds80hM-2_L99DRP7aNfJvG5h0W4oqF6Zn6m28AZ7N_Y2C_714HDvA7GPwzOvfAvJW3-KE',
  },
  {
    id: 'digital_masterpaint',
    title: 'Digital Masterpaint',
    description:
      'High-quality digital painting with thick impasto strokes, rich vibrant colors.',
    imageUrl:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuAO7-Z1fWv9lFq4dV4SeXwdn5YWUJML5cw49Nnn1wRAIqgT3MrlB3mQBy8gm9cHBfmPQkpgLNFz2XtFa_N7tqC13Z3Awyy3VIktj_VWoAvUfRI_efVcTLLeAabXi1-4yV9SfSpcxgQNq5DGo2wXfDUP9xcQtcr3jauqHfKymioQG1BJNEQ1DV1hceJdC0n2TdzTdCnjslXy5j8IDWkNar43KstXbFbCaD2Ft1W5R3qiVd57XkF9HDKFtLBOdq99bn3-3nczBeZMVTg',
  },
];

export const FRAME_SEQUENCE = [
  'Opening Hook',
  'Context Setup',
  'Inciting Beat',
  'Rising Action',
  'Conflict Spike',
  'Peak Moment',
  'Aftershock',
  'Resolution',
  'End Hook',
] as const;

export const FRAME_TAGS = ['High Contrast', 'Glitch', 'Soft Light', 'Abstract'] as const;

export const STYLE_TONE_BY_ID: Record<VisualStyleId, string> = {
  webtoon_cel: 'Anime Pulse',
  cinematic_realism: 'Cinematic',
  watercolor_dream: 'Orchestral',
  digital_masterpaint: 'Ambient',
};

export const FRAME_IMAGE_POOL: Record<VisualStyleId, string[]> = {
  cinematic_realism: [
    'https://lh3.googleusercontent.com/aida-public/AB6AXuBnCnU6D7BuXmld9I5SCll0KiFRrEWQ4YYO9cFB0FBzBt_KHqw-C2o2TLP0b3pCj5_OyXP2Dh_T7VHDwSh2IZTsYk6PiIqRtmtx2CqNF1MybxpNw6G6cllpaovO0FnsOxdNeekQavvgVrTb0ojh-paG52It16YgpGW2b23D5BWJnf6XeZqafeER1jtio9GFA1IlqFdlT0cJtPif-_w-iluGhCk3wc3HdcN4OcHuvsYv6PyADnAqQcPTNjGeGF1RunM8-NWPrF4WwaQ',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuBY4zQI3PwLuGj3TIuKavnbgNHd4mbwzR1T3e_cj97_myzRPrzVinde8ocwaGkET5emcpsXNh2alo_grZC_KNivseVGs-1sbD-CKgI5YhTIveovR5tRF4zd9So89a9ERFNyoFC-SdWOS9VrjW2YqmtxdrmcysUl1DuARZyxzsFO8sP0M6Uxaxg0Ol7m4A2GNSxpKawIzlVI8dIF9w_JmB_6eDF8sSRvdkwFedtsjvusGE3fCnvycw6omYD1zhK4zMFwMECu8M0lwRE',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuD-iAzr3g-7FFJCXAK9tTFUWnFtYHbkB5GUS68_T5RpxNZSsRvrrJTU5tO8CI1nwW84rlG4DIRtXVeDaYDO9bzx1t_e9hh_WvaMeVWF2zKsntWEHZ_FiBv7_jlov41sSdZPylIrWJXtEV0iF0Nz4ncLzEMZoynTc7B0Bc6TgAcogHBLGciKRwWgbm4SEjqUeQym-mi44coG9ISjfTte3wehzMRKgz41acuoklXthzsdr3RjbowzZht42fbJbg7mpHRuBAXR0xLR1Do',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuCoomK6_hfUaLB9AsTs-R3FGzOL94YWqMSbf_jfJZUt2Ew2NZlCOCOOAXosF4RNz6gKcsCDDAjH8hHJZoptX-E0LXyRDuSCKuGiR4jl4jVC_bKKpIeuWK__RjKjKW-YA50XkYq0nNaSbPbI1bWI5V8fe1XUhU-jJYyB2xg9pC2ZxoOK-Mkt70RK0Ele4-iqlGil_ZKPDqQ_g2hY9c1EQrN6KYZvBPcRPU8sinvYdNkHTn5uBI0yxCYwFIApTmwoTdPcD4WZyS-DcUg',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuAXge0moIBQVGww1tKvYiIcrinvcFDAe7dOHzVVozg7v6hmfEwJ8ukj1QfqCnO0ZOkHH6j_4-eZcXlzt3HBJtavn0oWArY_ZAs_CWMwHDzStl6U6asC6Q7AGWAS9_Gw_iS0sIW-3Htdjq2GwPAbqs-u5QbCk9__mdHJ2I7CriFnxQ3fW8ddYcLaBSLfqRCUyYeAzjnAyxkAOloqXE4rsQRettm209HXb2ehrWUNfFkUbFTaf8AFHO111PhcJDy59Bp6InvpXTjC_Fs',
    'https://lh3.googleusercontent.com/aida-public/AB6AXuAmmZ_T_18yZ-9-G685zUEdLm-NUNT6Yv5IWTjrPySfa_ALYHu_POxHGzQ2Owi2Z1DMOmN8J6x0RQaBGHWj0VWLqHVwMakDw30mEWo0uw0wRdki02k156IrPIq5JgyrAfUeEysix3kxnY1yJFn6qnpawh-743otAavgwTURZZoJLbO3cXLdz1_M1gWFVKRD6H14tWEGz8ZqvWzjdQVZaE1Pre_-9N8SsgZ5xP8wWuUxIaVLtRRj2pOFq_deShZ-0JhFMtbebNTbv-k',
  ],
  webtoon_cel: [
    'https://images.unsplash.com/photo-1542204625-de293a2750f8?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1526401485004-2aa7f3f5f3db?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1534670007418-fbb7f6cf32c3?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1519606247872-0440aae9b827?auto=format&fit=crop&w=900&q=80',
  ],
  watercolor_dream: [
    'https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1456081101716-74e616ab23d8?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1473181488821-2d23949a045a?auto=format&fit=crop&w=900&q=80',
  ],
  digital_masterpaint: [
    'https://images.unsplash.com/photo-1529429617124-aee711f2ff43?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1497215842964-222b430dc094?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1446776653964-20c1d3a81b06?auto=format&fit=crop&w=900&q=80',
    'https://images.unsplash.com/photo-1493612276216-ee3925520721?auto=format&fit=crop&w=900&q=80',
  ],
};
