/*
Copyright © 2020 Pavel Tisnovsky

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
package main

// Creates animation based on static GIF image + set of programmed rules. That
// animation displays the data flow for Insights Results Agregator consumer
// service.

// Link to generated documentation for this script:
// https://redhatinsights.github.io/insights-results-aggregator-utils/packages/anim_aggregator_consumer.html

import (
	"bufio"
	"image"
	"image/color"
	"image/draw"
	"image/gif"
	"os"
)

// readOriginal function tries to read the GIF file that contains the static
// input image. Animation to be created are based on this source image.
func readOriginal(filename string) *image.Paletted {
	// try to open the file specified by its name and check for any error
	fin, err := os.Open(filename)
	if err != nil {
		panic(err)
	}

	// file needs to be closed properly before that function ends
	defer func() {
		// try to close the file and check for any error that might
		// happened
		err := fin.Close()
		if err != nil {
			panic(err)
		}
	}()

	reader := bufio.NewReader(fin)

	// try to decode GIF frames from reader
	img, err := gif.Decode(reader)
	if err != nil {
		panic(err)
	}

	// we have to use image.Paletted, so it is needed to convert the image
	// into desired format
	return img.(*image.Paletted)
}

// writeAnimation function stores all images into GIF file. Each image (from
// `images` parameter) is stored as a GIF frame and delays between frames are
// provided by `delays` parameter. Please note that it would be possible to
// create smaller GIF image by applying external tool like `gifsicle` to the
// generated GIF file.
func writeAnimation(filename string, images []*image.Paletted, delays []int) {
	// try to open the file specified by its name and check for any error
	outfile, err := os.Create(filename)
	if err != nil {
		panic(err)
	}

	// file needs to be closed properly before that function ends
	defer func() {
		// try to close the file and check for any error that might
		// happened
		err := outfile.Close()
		if err != nil {
			panic(err)
		}
	}()

	// try to encode all GIF frames to output file
	err = gif.EncodeAll(outfile, &gif.GIF{
		Image: images,
		Delay: delays,
	})

	//  check if any error occured during EncodeAll operation
	if err != nil {
		panic(err)
	}
}

// drawAnt function draws one "marching" ant into the frame represented by
// `img` parameter. Position (center of ant) of marching ant is specified by
// `x0` and `y0`, and the color is selected by `col` parameter. There exists
// four colors that can be used.
//
// TODO: make color palette completely configurable
func drawAnt(img *image.Paletted, x0 int, y0 int, col int) {
	// standard color palette with four colors
	palette := make(map[int]color.RGBA, 4)

	// initialize color palette
	palette[0] = color.RGBA{200, 100, 100, 255}
	palette[1] = color.RGBA{00, 200, 00, 255}
	palette[2] = color.RGBA{255, 255, 255, 255}
	palette[3] = color.RGBA{105, 62, 200, 255}

	// rectangle that represents ant
	r := image.Rect(x0, y0, x0+10, y0+10)

	// draw the rectangle using selected color
	draw.Draw(img, r, &image.Uniform{palette[col]}, image.ZP, draw.Src)
}

// drawMarchingAnts functions draws all "marching" ants into the frame
// represented by `img` parameter. Currently marching ants are placed on four
// lines (two horizontal ones and two vertical ones).
//
// TODO: make this part completely configurable
func drawMarchingAnts(img *image.Paletted, step int) {
	// first vertical line
	for y := 388; y < 510; y += 20 {
		drawAnt(img, 904, y+step, 0)
	}

	// first horizontal line
	for x := 904; x > 798; x -= 20 {
		drawAnt(img, x-step, 530, 0)
	}

	// second vertical line
	for y := 561; y < 604; y += 20 {
		drawAnt(img, 760, y+step, 1)
	}

	// second horizontal line
	for x := 760; x > 694; x -= 20 {
		drawAnt(img, x-step, 624, 1)
	}

	// special unmovable blocks
	drawAnt(img, 664+27-10, 616+20-12, 2)
	drawAnt(img, 785, 529, 3)
	drawAnt(img, 786, 530, 3)
}

// main function is called by runtime after the tool has been started
// from command line.
func main() {
	// frames representing the whole animation stored in GIF file
	var images []*image.Paletted

	// delays between frames
	var delays []int

	// only 20 frames needs to be created
	steps := 20

	// create all frames to generate final animation
	for step := 0; step < steps; step++ {
		// read original image
		// TODO: make the file name configurable
		img := readOriginal("1.gif")

		// draw new frame based on original image
		drawMarchingAnts(img, step)

		// and add the frame into animation
		// TODO: make the delay configurable
		images = append(images, img)
		delays = append(delays, 10)
	}
	// write resulting animation (set of frames) into GIF file
	// TODO: make the file name configurable
	writeAnimation("2.gif", images, delays)
}
