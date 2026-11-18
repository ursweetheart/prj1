# photo-intake Specification

## Purpose
TBD - created by archiving change labelling-queue-feedback. Update Purpose after archive.

## Requirements

### Requirement: Batch upload answers at once
Staff SHALL upload all the photos of one upload into a project in a single request: up to 50 JPG, PNG or WebP files of at most 8 MB each. The system SHALL:
1. store each original;
2. queue one processing task per photo;
3. answer before any AI work, with each task's id, its photo path and the status "đang xử lý" (seq-1 steps 2-5).

A file of the wrong type or size SHALL be reported for that file only, and SHALL NOT be queued. Other roles SHALL get 403, anonymous callers 401.

#### Scenario: Upload 12 photos
- **WHEN** an architect uploads 12 photos into "Biệt thự Thảo Điền"
- **THEN** the answer comes back without waiting for the AI and lists 12 tasks with the status "đang xử lý"

#### Scenario: One bad file
- **WHEN** one of 5 files is a PDF
- **THEN** 4 tasks are queued and the PDF is reported as refused, with the reason

### Requirement: Queue processed in order, one photo at a time
A single worker SHALL take the queued tasks in the order they were queued (seq-1 loop "Với mỗi ảnh"). For each photo it SHALL:
1. classify it by the taxonomy dimensions;
2. extract its palette and detect its furniture;
3. compute its embedding;
4. save the proposed labels with their confidence as a draft space, and index its vector.

It SHALL then mark the task done with the space's id. A photo that fails SHALL be marked failed with a short reason, without stopping the queue. Tasks SHALL be kept in the database, so a restart resumes the queue, and a task that was running when the server stopped is retried once.

#### Scenario: AI error on one photo
- **WHEN** the third of 5 queued photos cannot be read
- **THEN** it is marked failed with the reason, and photos 4 and 5 are still processed

#### Scenario: Restart mid-queue
- **WHEN** the backend restarts while 6 tasks are waiting and one is running
- **THEN** after the restart the running one and the 6 waiting ones are processed

### Requirement: Progress and "done" notice on the review page
Staff SHALL be able to read the status of their tasks. After an upload, the review page SHALL:
- show how many photos are processed out of how many (seq-1 step 6);
- announce "Đã xử lý xong N ảnh" when every task has finished (step 16), listing failed photos with their reason;
- add the new drafts to the list without a manual reload.

The announcement SHALL be read out by screen readers.

#### Scenario: Watching progress
- **WHEN** an architect uploaded 4 photos and 2 are processed
- **THEN** the page shows "AI đã xử lý 2/4 ảnh" and, when all are done, "Đã xử lý xong 4 ảnh" with the 4 drafts in the list
