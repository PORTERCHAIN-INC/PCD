/**
 * Re-export shared blog author fallback from `@porterchain/types`.
 * Prefer CMS via `listBlogAuthors` / `getBlogAuthorRemote` when API is up.
 */
export {
  BLOG_AUTHORS as blogAuthors,
  getBlogAuthor as getAuthor,
  type BlogAuthor,
} from "@porterchain/types";
