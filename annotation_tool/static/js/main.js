// function updateImage(newImageUrl) {
//     document.getElementById('mainImage').src = newImageUrl;
// }

// function nextImage() {
//     fetch('/next_image', { method: 'POST' })
//         .then(response => response.json())
//         .then(data => updateImage(data.new_image_url))
//         .catch(error => console.error('Error fetching next image:', error));
// }

// function previousImage() {
//     fetch('/previous_image', { method: 'POST' })
//         .then(response => response.json())
//         .then(data => updateImage(data.new_image_url))
//         .catch(error => console.error('Error fetching previous image:', error));
// }

// // document.addEventListener('DOMContentLoaded', function() {
// //     const image = document.getElementById('mainImage');
// //     image.addEventListener('click', function(e) {
// //         const rect = image.getBoundingClientRect();
// //         const x = e.clientX - rect.left;
// //         const y = e.clientY - rect.top;

// //         // Send coordinates to the server
// //         fetch('/save_coordinates', {
// //             method: 'POST',
// //             headers: {
// //                 'Content-Type': 'application/json'
// //             },
// //             body: JSON.stringify({ x: x, y: y, image_path: image.src })
// //         })
// //         .then(response => response.json())
// //         .then(data => console.log('Coordinates saved:', data))
// //         .catch(error => console.error('Error saving coordinates:', error));
// //     });
// // });

// document.addEventListener('DOMContentLoaded', function() {
//     const canvas = document.getElementById('imageCanvas');
//     const ctx = canvas.getContext('2d');
//     const image = new Image();
//     let boxes = JSON.parse(document.getElementById('boxesData').value); // Assuming boxes data is injected into HTML

//     image.onload = function() {
//         canvas.width = image.width;
//         canvas.height = image.height;
//         ctx.drawImage(image, 0, 0);
//         boxes.forEach(box => drawRectangle(ctx, box));
//     };
//     image.src = document.getElementById('mainImage').value; // Image URL injected into HTML

//     function drawRectangle(ctx, box) {
//         ctx.strokeStyle = 'blue';
//         ctx.lineWidth = 2;
//         ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);
//     }
// });

// function updateServerBoxes() {
//     // Example function to send updated boxes to server
//     fetch('/update_boxes', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({
//             mainImage: document.getElementById('mainImage').value,
//             boxes: boxes // Updated boxes array
//         })
//     })
//     .then(response => response.json())
//     .then(data => console.log(data))
//     .catch(error => console.error('Error:', error));
// }

document.addEventListener('DOMContentLoaded', function() {
    const image = document.getElementById('mainImage');
    const canvas = document.getElementById('imageCanvas');
    const ctx = canvas.getContext('2d');
    let startX, startY; // Variables to store the start coordinates

    image.onload = function() {
        canvas.width = image.clientWidth;
        canvas.height = image.clientHeight;
        drawBoxes();
    };

    canvas.addEventListener('mousedown', function(e) {
        const rect = canvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
    });

    canvas.addEventListener('mouseup', function(e) {
        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;

        // Send coordinates to the server
        fetch('/save_coordinates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                x1: Math.min(startX, endX),
                y1: Math.min(startY, endY),
                x2: Math.max(startX, endX),
                y2: Math.max(startY, endY),
                image_path: image.src
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Coordinates saved:', data);
            drawRectangle(ctx, startX, startY, endX - startX, endY - startY); // Draw the new box
        })
        .catch(error => console.error('Error saving coordinates:', error));
    });

    function drawBoxes() {
        const boxes = JSON.parse(document.getElementById('boxesData').value);
        boxes.forEach(box => {
            drawRectangle(ctx, box[0], box[1], box[2] - box[0], box[3] - box[1]);
        });
    }

    function drawRectangle(ctx, x, y, width, height) {
        ctx.strokeStyle = 'blue';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
    }
    
    // Update boxes on navigation
    window.nextImage = function() {
        fetch('/next_image', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                image.src = data.new_image_url;
                drawBoxes(); // Re-draw boxes for new image
            })
            .catch(error => console.error('Error fetching next image:', error));
    };

    window.previousImage = function() {
        fetch('/previous_image', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                image.src = data.new_image_url;
                drawBoxes(); // Re-draw boxes for new image
            })
            .catch(error => console.error('Error fetching previous image:', error));
    };
});
